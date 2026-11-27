"""Run the built kit-2 helper libraries (32-bit ARM code) in Unicorn against a model camera, and check every level.

    python -I -B emu_m3og.py                 all scenarios against the real 4.04 av-cam.bin (a7m3_map/work/extracted)
    python -I -B emu_m3og.py --show dump     print the dump's result text

The model camera: physical memory with av-cam.bin at 0x035C6000 (its reservation up to 0x048C6000 zero-filled), a
kernel-log ring at 0x035A5000 and an application-log ring at 0x03524FC0; the runtime drive table rows of the 4K
full-frame drive filled in for one TV system (they are zero in the file); /dev/mem served by pread64/pwrite64; a small
/proc and /sys; /tmp_network (RAM tmpfs) and /tmp/jiritsu.
The library is loaded as the dynamic linker would (PT_LOAD segments, R_ARM_RELATIVE relocations) and its DT_INIT_ARRAY
entries are called. Every system call the library makes is handled here; any other one fails the run.
"""
import hashlib
import io
import json
import struct
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_INTR, UC_MODE_ARM, Uc
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                               UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R7, UC_ARM_REG_SP)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
AVCAM = ROOT / 'work' / 'extracted' / 'a7m3_404' / '0700_part_image' / 'dev' / 'nflasha3' / 'av-cam.bin'
KEMCO = ROOT / 'work' / 'extracted' / 'a7m3_404' / 'update' / '0800_appli' / 'setting' / 'kemco.txt'
DESIGN = ROOT / 'modding' / 'designs' / 'og_m3_v2.json'
LIBS = {n: HERE / ('libJit_m3og_%s.so' % n) for n in ('dump', 'test1', 'test2', 'test3', 'test4', 'test5', 'putback', 'norestart', 'nocheck')}

BASE, STACK, STACK_SZ, RET = 0x10000000, 0x7E000000, 0x100000, 0x7F000000
AV_PHYS, AV_END, KLOG_PHYS, KLOG_LEN = 0x035C6000, 0x048C6000, 0x035A5000, 0x20000
ALOG_PHYS, ALOG_LEN = 0x03524FC0, 0x60040
MEM_BASE = ALOG_PHYS                    # the model's memory starts at the application log ring
EEXIST, ENOENT, EBADF, EFAULT, ENOTDIR = 17, 2, 9, 14, 20


class Camera:
    """The model camera's memory and files."""

    def __init__(self, tmpfs=True, devmem=True, system='59.94'):
        img = AVCAM.read_bytes()
        self.mem = bytearray(AV_PHYS - MEM_BASE) + bytearray(img) + bytearray(AV_END - AV_PHYS - len(img))
        self.mem_base = MEM_BASE
        klog = (b'<6>[    0.000000] Booting Linux on physical CPU 0\n<6>[    1.234567] wlan0: address 12:34:56:ab:cd:ef\n'
                b'<4>[    2.000000] liro: resume (WBI)\n')
        self.mem[KLOG_PHYS - MEM_BASE:KLOG_PHYS - MEM_BASE + len(klog)] = klog
        alog = (b'\x01\x02\x03\x00\x00[IMG] S-Ele Refresh!\n\xff\xfe\xfdLost CAMOUT_V now[vfc:5 frc:6], camoutv[vfc:4 frc:6]\n'
                b'net aa:bb:cc:dd:ee:01 up\n')
        self.mem[0x40:0x40 + len(alog)] = alog
        # the runtime drive tables are zero in the file: the firmware builds them at start for the active TV system.
        # The model fills in what the helper reads: HMAX of both 4K full-frame slots, the cycle pair and the derived byte.
        tb = json.loads(DESIGN.read_text())['timing_blocks']
        if system is not None:
            t = tb[system]
            other = tb['50' if system == '59.94' else '59.94']
            row = int(t['runtime_pair_va'], 16) - 0x68 - 0x60000000 - MEM_BASE
            orow = int(other['runtime_pair_va'], 16) - 0x68 - 0x60000000 - MEM_BASE
            self.mem[row + 8:row + 12] = struct.pack('<I', 525)
            self.mem[orow + 8:orow + 12] = struct.pack('<I', 1)
            self.mem[row + 0x68:row + 0x70] = struct.pack('<II', *t['stock_pair'])
            self.mem[int(t['derived_byte_va'], 16) - 0x60000000 - MEM_BASE] = t['stock_derived_byte']
            self.mem[row + 0x50:row + 0x54] = bytes.fromhex(t['size_rt_stock'])
            a = int(t['readout_rt_va'], 16) - 0x60000000 - MEM_BASE
            row1c = bytearray(bytes.fromhex(t['readout_rt_stock']))
            row1c[6:12] = struct.pack('<3H', 3564, 2376, 4283)     # words 3 to 5 are live on a camera (both testers' stock dumps)
            self.mem[a:a + 0x12] = row1c
        self.system = system
        cmdline = ' '.join(ln.strip() for ln in KEMCO.read_text().splitlines()[1:] if ln.strip())
        self.files = {'/proc/cmdline': cmdline.encode() + b'\n', '/proc/version': b'Linux version 3.0.27 (simulated)\n',
                      '/proc/cpuinfo': b'Processor\t: ARMv7 Processor rev 1 (v7l)\nFeatures\t: swp half thumb fastmult vfp edsp vfpv3 vfpv3d16\nSerial\t\t: 0123456789abcdef\n',
                      '/proc/meminfo': b'MemTotal: 1 kB\n', '/proc/uptime': b'12.00 10.00\n',
                      '/sys/module/liro/parameters/adr': b'0x035c6000\n'}
        self.dirs = {'/sys/module/liro/parameters': ['adr'], '/tmp_network': [], '/tmp/jiritsu': ['libJit.so']}
        if not tmpfs:
            del self.dirs['/tmp_network']
        self.devmem = devmem
        self.created = {}
        self.fail_write_at = None
        self.writes = []

    def rd(self, phys, n):
        o = phys - self.mem_base
        if o < 0 or o + n > len(self.mem):
            return None
        return bytes(self.mem[o:o + n])

    def wr(self, phys, data):
        o = phys - self.mem_base
        if o < 0 or o + len(data) > len(self.mem):
            return False
        self.mem[o:o + len(data)] = data
        return True


class Run:
    def __init__(self, lib, cam):
        self.cam = cam
        self.fds = {}
        self.next_fd = 3
        self.bad = None
        self.calls = []
        data = Path(lib).read_bytes()
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        elf = ELFFile(io.BytesIO(data))                              # no open file left behind (Windows deletes)
        hi = max(s['p_vaddr'] + s['p_memsz'] for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD')
        self.uc.mem_map(BASE, (hi + 0xFFFF) & ~0xFFFF)
        for s in elf.iter_segments():
            if s['p_type'] == 'PT_LOAD':
                self.uc.mem_write(BASE + s['p_vaddr'], data[s['p_offset']:s['p_offset'] + s['p_filesz']])
        for sec in elf.iter_sections():
            if sec.name == '.rel.dyn':
                for r in sec.iter_relocations():
                    if r['r_info_type'] != 23:                        # R_ARM_RELATIVE only: the library has no imports
                        raise AssertionError('relocation type %d' % r['r_info_type'])
                    a = BASE + r['r_offset']
                    v = struct.unpack('<I', self.uc.mem_read(a, 4))[0]
                    self.uc.mem_write(a, struct.pack('<I', (v + BASE) & 0xFFFFFFFF))
        dyn = {t.entry.d_tag: t.entry.d_val for t in elf.get_section_by_name('.dynamic').iter_tags()}
        self.init = []
        if 'DT_INIT_ARRAY' in dyn:
            for k in range(dyn['DT_INIT_ARRAYSZ'] // 4):
                self.init.append(struct.unpack('<I', self.uc.mem_read(BASE + dyn['DT_INIT_ARRAY'] + 4 * k, 4))[0])
        self.uc.mem_map(STACK - STACK_SZ, STACK_SZ + 0x1000)
        self.uc.mem_map(RET, 0x1000)
        self.uc.mem_map(0x6F000000, 0x10000)                          # scratch for the model's own strings
        self.uc.hook_add(UC_HOOK_INTR, self.svc)

    def cstr(self, a):
        b = bytearray()
        while len(b) < 512:
            c = self.uc.mem_read(a + len(b), 1)
            if c == b'\0':
                break
            b += c
        return b.decode()

    def reg(self, r):
        return self.uc.reg_read(r)

    def svc(self, uc, intno, _):
        if intno != 2:
            self.bad = 'interrupt %d' % intno
            uc.emu_stop()
            return
        n = self.reg(UC_ARM_REG_R7)
        a = [self.reg(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5)]
        try:
            r = self.sys(n, a)
        except Exception as exc:  # noqa: BLE001
            self.bad = 'syscall %d: %r' % (n, exc)
            uc.emu_stop()
            return
        self.calls.append((n, r))
        uc.reg_write(UC_ARM_REG_R0, r & 0xFFFFFFFF)

    def sys(self, n, a):
        cam = self.cam
        if n == 5:                                                    # open
            path, flags = self.cstr(a[0]), a[1]
            fd = self.next_fd
            if path == '/dev/mem':
                if not cam.devmem:
                    return -ENOENT
                self.fds[fd] = ('mem', flags & 3)
            elif flags & 0x40:                                        # O_CREAT
                d = path.rsplit('/', 1)[0]
                if path in cam.created or path in cam.files:
                    return -EEXIST
                if d not in cam.dirs:
                    return -ENOENT
                if path not in ('/tmp_network/m3og_result.txt', '/tmp/jiritsu/m3og_result.txt'):
                    raise AssertionError('creates ' + path)
                cam.created[path] = bytearray()
                self.fds[fd] = ('out', path)
            elif flags & 0x4000:                                      # O_DIRECTORY
                if path not in cam.dirs:
                    return -ENOENT
                self.fds[fd] = ('dir', path, False)
            else:
                if flags & 3:
                    raise AssertionError('opens %s for writing' % path)
                if path not in cam.files:
                    return -ENOENT
                self.fds[fd] = ('file', cam.files[path], 0)
            self.next_fd += 1
            return fd
        if n == 6:                                                    # close
            return 0 if self.fds.pop(a[0], None) else -EBADF
        if n == 3:                                                    # read
            f = self.fds.get(a[0])
            if not f or f[0] != 'file':
                return -EBADF
            chunk = f[1][f[2]:f[2] + a[2]]
            self.uc.mem_write(a[1], chunk)
            self.fds[a[0]] = ('file', f[1], f[2] + len(chunk))
            return len(chunk)
        if n == 4:                                                    # write
            f = self.fds.get(a[0])
            if not f or f[0] != 'out':
                raise AssertionError('write to fd %d (%r)' % (a[0], f and f[0]))
            cam.created[f[1]] += self.uc.mem_read(a[1], a[2])
            return a[2]
        if n in (180, 181):                                           # pread64 / pwrite64 (offset in r4:r5)
            f = self.fds.get(a[0])
            if not f or f[0] != 'mem':
                return -EBADF
            off = a[4] | (a[5] << 32)
            if n == 180:
                b = cam.rd(off, a[2])
                if b is None:
                    return -EFAULT
                self.uc.mem_write(a[1], b)
                return a[2]
            if f[1] != 2:
                raise AssertionError('pwrite on a read-only /dev/mem')
            if cam.fail_write_at is not None and len(cam.writes) == cam.fail_write_at:
                cam.writes.append((off, None))
                return -EFAULT
            data = bytes(self.uc.mem_read(a[1], a[2]))
            if not cam.wr(off, data):
                return -EFAULT
            cam.writes.append((off, data))
            return a[2]
        if n == 217:                                                  # getdents64
            f = self.fds.get(a[0])
            if not f or f[0] != 'dir':
                return -ENOTDIR
            if f[2]:
                return 0
            out = b''
            for name in cam.dirs[f[1]]:
                nm = name.encode() + b'\0'
                rl = (19 + len(nm) + 7) & ~7
                out += struct.pack('<QqHB', 1, 0, rl, 8) + nm + bytes(rl - 19 - len(nm))
            self.uc.mem_write(a[1], out[:a[2]])
            self.fds[a[0]] = ('dir', f[1], True)
            return len(out)
        if n == 201:
            return 0                                                  # geteuid32: root
        if n == 20:
            return 1234
        if n == 118:
            return 0                                                  # fsync
        raise AssertionError('system call %d is not one the helper may make' % n)

    def go(self):
        for fn in self.init:
            self.uc.reg_write(UC_ARM_REG_SP, STACK - 0x100)
            self.uc.reg_write(UC_ARM_REG_LR, RET)
            self.uc.emu_start(fn, RET, count=200_000_000)
            if self.bad:
                break
            if self.uc.reg_read(UC_ARM_REG_PC) != RET:
                self.bad = 'did not return (pc %#x)' % self.uc.reg_read(UC_ARM_REG_PC)
        return self


def run(level, cam):
    r = Run(LIBS[level], cam).go()
    text = b''.join(bytes(v) for v in cam.created.values()).decode('utf8', 'replace')
    return r, text


def main():
    design = json.loads(DESIGN.read_text())
    stock = Camera().mem
    steps = design['steps']
    tb = design['timing_blocks']
    P = lambda va: (int(va, 16) if isinstance(va, str) else va) - 0x60000000 - MEM_BASE   # noqa: E731  (model offset of a VA)

    def blocks(system):
        t = tb[system]
        return [(P(0x646F0320), 5496), (P(0x63E0D798), 0x540), (P(0x63E12B98), 0x540),
                (P(t['rom_pair_va']), 8), (P(t['runtime_pair_va']), 8), (P(t['derived_byte_va']), 1),
                (P(t['size_rom_va']), 4), (P(t['size_rt_va']), 4), (P(t['readout_rt_va']) + 4, 2), (P(t['readout_rt_va']) + 0xE, 2)]

    def diff(m, ref=None):
        ref = stock if ref is None else ref
        return [i for i in range(len(m)) if m[i] != ref[i]]

    def in_blocks(offs, system='59.94'):
        return all(any(p <= o < p + n for p, n in blocks(system)) for o in offs)

    def sensor_ok(mem, name):
        return all(mem[P(s['va'])] == int(s['new'], 16) for s in steps[name]['sensor_sites'])

    def records_ok(mem, name):
        return all(struct.unpack_from('<H', mem, P(va) + 2 * w['word'])[0] == w['new']
                   for va, ws in steps[name]['records'].items() for w in ws)

    def timing_ok(mem, name, system):
        t, want = tb[system], steps[name]['timing'][system]
        pair = struct.pack('<II', want['H2'], want['V2'])
        return (bytes(mem[P(t['rom_pair_va']):P(t['rom_pair_va']) + 8]) == pair
                and bytes(mem[P(t['runtime_pair_va']):P(t['runtime_pair_va']) + 8]) == pair
                and mem[P(t['derived_byte_va'])] == want['derived_byte'])

    results = []

    def check(cond, what):
        results.append((bool(cond), what))
        print('%-4s %s' % ('pass' if cond else 'FAIL', what))

    if '--show' in sys.argv:
        _r, text = run(sys.argv[sys.argv.index('--show') + 1], Camera())
        print(text)
        return

    N_MEM = 18 + 10                                                   # 18 read-only ranges + the ten blocks
    # 1. dump on a stock camera
    cam = Camera()
    r, t = run('dump', cam)
    check(not r.bad, 'dump: runs to the end (%s)' % (r.bad or 'ok'))
    check('VERDICT READY (stock)' in t and t.count('SAME as the 4.04 file') == 3 and t.count('  matches 4.04') == 16,
          'dump: LIRO header + 2 code ranges SAME, 16 image pages reported, verdict READY (stock)')
    check('tv system 59.94 (slot 28)' in t and t.count('  STOCK\n') == 10, 'dump: TV system 59.94 found, ten blocks STOCK')
    check(not cam.writes and diff(cam.mem) == [], 'dump: memory untouched, no pwrite')
    check('0123456789abcdef' not in t and 'not copied by m3og' in t, 'dump: the cpuinfo Serial line is not copied')
    check('12:34:56:ab:cd:ef' not in t and 'xx:xx:xx:xx:xx:xx' in t and 'liro: resume (WBI)' in t, 'dump: kernel log copied as text, MAC address blanked')
    alog = t[t.index('== alog phys'):] if '== alog phys' in t else ''
    check('S-Ele Refresh!' in alog and 'Lost CAMOUT_V now[vfc:5 frc:6]' in alog and 'aa:bb:cc:dd:ee:01' not in alog
          and '.[IMG]' in alog and '..' not in alog.split('== end')[0],
          'dump: application log copied as text, MAC address blanked, binary runs squeezed to one dot')
    check('== dir /sys/module/liro/parameters' in t and '= 0x035c6000' in t, 'dump: liro parameters listed with values')
    check(t.count('== mem ') == N_MEM and '== mem sgc1_param' in t and '== mem refresh_state' in t and '== mem timing_rt_ntsc' in t
          and '== mem cam_flags' in t and '== mem cam_status' in t and '== mem sync_stamps' in t and '== mem cam_core_state' in t and 'GUARD flag byte 0x00  refresh loop STOCK' in t
          and t.rstrip().split('\n')[-1].startswith('== done'), 'dump: %d memory ranges (new: SGC1 block, refresh state, timing blocks) and the done line' % N_MEM)
    check(list(cam.created) == ['/tmp_network/m3og_result.txt'], 'dump: result on /tmp_network (RAM)')
    # 1b. the first camera run: the first image pages hold live data. They are reported and the run goes on
    cam = Camera()
    for o in (0x200, 0x1004):
        cam.mem[AV_PHYS - MEM_BASE + o] ^= 0x5A
    r, t = run('dump', cam)
    check('VERDICT READY (stock)' in t and t.count('differs from 4.04 (live data, not required)') == 2 and t.count('== mem image_page') == 2,
          'live data in image pages 0 and 1: dump READY (stock), both pages reported and copied out')
    r, t = run('test2', cam_from(bytes(cam.mem)))
    check('DONE: ' in t and 'READY (test 2 applied)' in t, 'live data in image pages 0 and 1: test2 DONE')
    # 1c. a 50-system camera, and one whose slots are not recognised
    cam = Camera(system='50')
    r, t = run('dump', cam)
    check('tv system 50 (slot 27)' in t and 'VERDICT READY (stock)' in t and '== mem timing_rt_pal' in t, 'dump on a 50-system camera: slot 27, READY (stock)')
    pal_stock = bytes(cam.mem)
    for name in ('dump', 'test2'):
        cam = Camera(system=None)
        r, t = run(name, cam)
        check(not r.bad and 'tv system NOT RECOGNISED' in t and 'NOT READY (the TV system slot' in t and not cam.writes
              and (name == 'dump' or 'NOT DONE: the TV system slot' in t),
              '%s with no recognisable TV-system slot: NOT READY, nothing written' % name)
    # 1d. a full application log (every byte printable): the result stays under the 1 MB tmpfs and keeps its last line
    cam = Camera()
    cam.mem[0:ALOG_LEN] = (b'0123456789abcdefghijklmnopqrstuvwxyz ' * (ALOG_LEN // 37 + 1))[:ALOG_LEN]
    r, t = run('dump', cam)
    size = sum(len(v) for v in cam.created.values())
    check(not r.bad and size < 1024 * 1024 and t.rstrip().split('\n')[-1].startswith('== done') and t.count('== mem ') == N_MEM,
          'dump with a full application log: %d bytes, under the 1 MB RAM disk, done line present' % size)
    # 2. test 1 on stock
    cam = Camera()
    r, t = run('test1', cam)
    d = diff(cam.mem)
    sites = sorted(P(s['va']) for s in steps['test1']['sensor_sites'])
    check(not r.bad and 'DONE: ' in t and 'READY (test 1 applied)' in t, 'test1: DONE, then READY (test 1 applied)')
    check(d == sites and sensor_ok(cam.mem, 'test1'), 'test1: exactly the 7 sensor bytes changed, to the design values')
    mem = {'test1': bytes(cam.mem)}
    # 3. test 2 on top of test 1; then tests 2, 3, 4 on stock
    r, t = run('test2', cam_from(mem['test1']))
    check(not r.bad and 'DONE: ' in t and 'READY (test 2 applied)' in t, 'test2 after test1: DONE, READY (test 2 applied)')
    for n, name in ((2, 'test2'), (3, 'test3'), (4, 'test4'), (5, 'test5')):
        cam = Camera()
        r, t = run(name, cam)
        dn = diff(cam.mem)
        check(not r.bad and 'DONE: ' in t and ('READY (test %d applied)' % n) in t and in_blocks(dn),
              '%s on stock: DONE, READY (test %d applied); %d bytes changed, all inside the ten blocks' % (name, n, len(dn)))
        if 'size' in steps[name]:
            sz = steps[name]['size']['59.94']
            t5 = tb['59.94']
            check(struct.unpack_from('<I', cam.mem, P(t5['size_rom_va']))[0] == sz['inner_rows']
                  and bytes(cam.mem[P(t5['size_rt_va']):P(t5['size_rt_va']) + 4]).hex() == sz['size_rt']
                  and list(struct.unpack_from('<9H', cam.mem, P(t5['readout_rt_va']))) == sz['readout_words'][:3] + [3564, 2376, 4283] + sz['readout_words'][6:],
                  '%s: size row inner height %d in the ROM row and the runtime entry, read-out words 2 and 7 = %d, the live words 3 to 5 untouched' % (name, sz['inner_rows'], sz['readout_words'][2]))
        else:
            t5 = tb['59.94']
            check(struct.unpack_from('<I', cam.mem, P(t5['size_rom_va']))[0] == 3376
                  and list(struct.unpack_from('<9H', cam.mem, P(t5['readout_rt_va']))) == t5['readout_words_stock'][:3] + [3564, 2376, 4283] + t5['readout_words_stock'][6:],
                  '%s: the size row and the read-out row stay stock' % name)
        check(sensor_ok(cam.mem, name) and records_ok(cam.mem, name) and timing_ok(cam.mem, name, '59.94'),
              '%s: sensor window %d rows from %d, 2 x %d record words, timing pair %d / %d and derived byte hold the design values' % (
                  name, steps[name]['rows'], steps[name]['first_row'], steps[name]['record_words_changed'],
                  steps[name]['timing']['59.94']['H2'], steps[name]['timing']['59.94']['V2']))
        check(bytes(cam.mem[P(tb['50']['rom_pair_va']):P(tb['50']['rom_pair_va']) + 8]) == bytes(stock[P(tb['50']['rom_pair_va']):P(tb['50']['rom_pair_va']) + 8]),
              '%s on a 59.94 camera: the 50-system row is not touched' % name)
        mem[name] = bytes(cam.mem)
    cam = cam_from(pal_stock, system='50')
    r, t = run('test2', cam)
    dn = diff(cam.mem, pal_stock)
    pal_t2 = bytes(cam.mem)
    check(not r.bad and 'READY (test 2 applied)' in t and in_blocks(dn, '50') and timing_ok(cam.mem, 'test2', '50'),
          'test2 on a 50-system camera: DONE; the slot-27 pair holds %d / %d' % (steps['test2']['timing']['50']['H2'], steps['test2']['timing']['50']['V2']))
    cam = cam_from(pal_t2, system='50')
    r, t = run('putback', cam)
    check('READY (stock)' in t and bytes(cam.mem) == pal_stock, 'putback on the 50-system camera: memory as before')
    # 4. one test over another refuses
    for over, under in (('test1', 'test2'), ('test3', 'test2'), ('test2', 'test4'), ('test4', 'test3'), ('test4', 'test5'), ('test3', 'test5')):
        cam = cam_from(mem[under])
        r, t = run(over, cam)
        check(not r.bad and 'run the put-back first' in t and not cam.writes and bytes(cam.mem) == mem[under],
              '%s over %s: NOT DONE, nothing written' % (over, under))
    # 5. put back
    for name in ('test1', 'test2', 'test3', 'test4', 'test5'):
        cam = cam_from(mem[name])
        r, t = run('putback', cam)
        check(not r.bad and 'DONE: ' in t and 'READY (stock)' in t and bytes(cam.mem) == bytes(stock), 'putback after %s: memory equals 4.04 again' % name)
    cam = Camera()
    r, t = run('putback', cam)
    check('NOTHING TO DO' in t and not cam.writes, 'putback on stock: NOTHING TO DO, no write')
    cam = cam_from(mem['test3'])
    r, t = run('test5', cam)
    check(not r.bad and 'DONE: ' in t and 'READY (test 5 applied)' in t and bytes(cam.mem) == mem['test5'],
          'test5 after test3: DONE, adds only the size blocks, READY (test 5 applied)')
    for n, name in ((2, 'test2'), (3, 'test3'), (4, 'test4'), (5, 'test5')):
        r, t = run('dump', cam_from(mem[name]))
        check(('VERDICT READY (test %d applied)' % n) in t, 'dump after %s: READY (test %d applied)' % (name, n))
    # 5b. the second camera run's state (v2 test 2: sensor + records, timing pair still stock) is reported as partly applied
    cam = cam_from(mem['test2'])
    for p, n in blocks('59.94')[3:]:
        cam.mem[p:p + n] = stock[p:p + n]
    v2_state = bytes(cam.mem)
    r, t = run('dump', cam)
    check('NOT READY (the design\'s bytes are partly applied' in t, 'v2 test-2 state (timing pair stock): dump says partly applied')
    cam = cam_from(v2_state)
    r, t = run('test2', cam)
    check('READY (test 2 applied)' in t and bytes(cam.mem) == mem['test2'], 'test2 over the v2 test-2 state: completes it')
    # 5c. v4: the refresh loop's switch byte (bit 0x40 = no forced restart, bit 0x02 = loop off); other bits are kept
    G = P(0x6433CD5E)
    for name, bit, word in (('norestart', 0x40, 'refresh loop on, NO FORCED RESTART'), ('nocheck', 0x02, 'refresh loop OFF')):
        cam = cam_from(mem['test4'])
        cam.mem[G] = 0x81
        r, t = run(name, cam)
        check(not r.bad and 'DONE: 0x00000001 bytes' in t and cam.mem[G] == (0x81 | bit) and diff(cam.mem, mem['test4']) == [G]
              and len(cam.writes) == 1 and 'READY (test 4 applied)' in t and t.count('GUARD flag byte') == 2 and word in t,
              '%s over test 4: one byte written, only bit %#04x set, the test bytes untouched' % (name, bit))
        cam2 = cam_from(bytes(cam.mem))
        r, t = run(name, cam2)
        check('NOTHING TO DO' in t and not cam2.writes, '%s again: NOTHING TO DO, no write' % name)
        r, t = run('dump', cam_from(bytes(cam.mem)))
        check(word in t and 'READY (test 4 applied)' in t, 'dump after %s: reports "%s"' % (name, word))
        cam = Camera(system=None)
        r, t = run(name, cam)
        check('DONE: ' in t and cam.mem[G] == bit, '%s needs no TV-system slot: DONE' % name)
        cam = Camera()
        cam.mem[P(0x637B4000)] ^= 0xFF
        r, t = run(name, cam)
        check('NOT DONE: av-cam identity' in t and not cam.writes, '%s with a differing code range: NOT DONE, no write' % name)
    cam = cam_from(mem['test4'])
    cam.mem[G] = 0x81 | 0x42
    r, t = run('putback', cam)
    d = diff(cam.mem)
    check(not r.bad and 'guard: switch bits cleared' in t and 'DONE: ' in t and 'READY (stock)' in t and d == [G] and cam.mem[G] == 0x81
          and 'refresh loop STOCK' in t.split('after:')[-1],
          'putback after test 4 + both switches: blocks equal 4.04, both switch bits cleared, the other bits kept')
    cam = Camera()
    cam.mem[G] = 0x40
    r, t = run('putback', cam)
    check('DONE: 0x00000001 bytes written in 0x00000001 runs' in t and bytes(cam.mem) == bytes(stock), 'putback with only a switch set: one byte, memory equals 4.04')
    cam = Camera(system=None)
    cam.mem[G] = 0x02
    r, t = run('putback', cam)
    check('guard: switch bits cleared' in t and cam.mem[G] == 0 and 'NOT DONE: the TV system slot' in t,
          'putback with no recognisable TV-system slot: the switch is still cleared')
    # 6. identity differs -> nothing written; the dump still reads the tables if the header matches
    cam = Camera()
    cam.mem[P(0x637B4000)] ^= 0xFF
    r, t = run('test2', cam)
    check(not r.bad and 'DIFFERS from the 4.04 file' in t and 'NOT DONE: av-cam identity' in t and not cam.writes, 'required code range differs: NOT DONE, no write')
    cam = Camera()
    cam.mem[P(0x637B4000)] ^= 0xFF
    r, t = run('dump', cam)
    check('VERDICT NOT READY' in t and t.count('== mem ') == N_MEM and '== blocks' in t, 'required code range differs: the dump still reads the blocks and tables')
    cam = Camera()
    cam.mem[AV_PHYS + 4 - MEM_BASE] ^= 1
    r, t = run('dump', cam)
    check('VERDICT NOT READY' in t and '== mem ' not in t, 'LIRO header differs: dump reads no av-cam tables')
    # 7. a block byte that is neither stock nor a test byte
    for name, va in (('fe_rec_0a', 0x63E0D798 + 0x100), ('timing_rt_ntsc', int(tb['59.94']['runtime_pair_va'], 16))):
        cam = Camera()
        cam.mem[P(va)] ^= 0x5A
        r, t = run('test2', cam)
        check(('NOT DONE: block ' + name) in t and not cam.writes, 'foreign byte in block %s: NOT DONE, no write' % name)
    # 8. a write fails part-way -> everything written is put back
    for at in (5, 139):
        cam = Camera()
        cam.fail_write_at = at
        r, t = run('test2', cam)
        check(not r.bad and 'putting back' in t and 'everything written was put back' in t and bytes(cam.mem) == bytes(stock),
              'write failure at write %d: rolled back, memory equals 4.04' % at)
    # 9. earlier result present -> does nothing at all
    cam = Camera()
    cam.files['/tmp_network/m3og_result.txt'] = b'old'
    r, t = run('test1', cam)
    check(not r.bad and not cam.created and not cam.writes and not any(n == 180 for n, _ in r.calls), 'result already there: nothing read, nothing written')
    # 10. no /tmp_network -> result in /tmp/jiritsu; no /dev/mem -> NOT READY
    cam = Camera(tmpfs=False)
    r, t = run('dump', cam)
    check(list(cam.created) == ['/tmp/jiritsu/m3og_result.txt'] and 'READY (stock)' in t, 'no /tmp_network: result in /tmp/jiritsu')
    cam = Camera(devmem=False)
    r, t = run('test1', cam)
    check('no /dev/mem' in t and not cam.writes, 'no /dev/mem: NOT READY, nothing written')
    # 11. the built files: size, no imports, no FP/SIMD instruction, no system call outside the list
    for n, p in LIBS.items():
        facts = audit(p)
        check(0 < p.stat().st_size <= 65520, '%s: %d bytes, fits one upload packet; sha256 %s' % (p.name, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()[:16]))
        check(not facts['needed'] and not facts['undefined'] and facts['fp_simd'] == 0,
              '%s: no imports; %d instructions, none FP/SIMD (%d literal-pool bytes)' % (p.name, facts['insns'], facts['undecoded']))
        # 0 occurs as r7 zeroed for use as an ordinary register (as a system call it is restart_syscall, which does nothing
        # here); every call actually made in the scenarios above went through Run.sys, which fails on any other number
        allowed = {0, 3, 4, 5, 6, 20, 118, 180, 201, 217} | ({181} if n != 'dump' else set())
        check(facts['syscalls'] <= allowed and (181 in facts['r7_immediates']) == (n != 'dump'),
              '%s: %d svc sites, system call numbers %s%s' % (p.name, facts['svc'], sorted(facts['syscalls']),
                                                             '' if n != 'dump' else ' (181 = pwrite64 is never loaded in the read-only build)'))
    bad = [w for ok, w in results if not ok]
    print('\n%d checks, %d failed' % (len(results), len(bad)))
    sys.exit(1 if bad else 0)


def audit(path):
    """Static facts of a built library: imports, every instruction of .text (decoded linearly; the library keeps its
    data in .rodata), FP/SIMD instructions, and the system call numbers loaded into r7 right before each svc."""
    import capstone
    elf = ELFFile(io.BytesIO(Path(path).read_bytes()))
    dyn = elf.get_section_by_name('.dynamic')
    needed = [t.needed for t in dyn.iter_tags() if t.entry.d_tag == 'DT_NEEDED']
    undefined = [s.name for s in elf.get_section_by_name('.dynsym').iter_symbols() if s['st_shndx'] == 'SHN_UNDEF' and s.name]
    text = elf.get_section_by_name('.text')
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    d, base = text.data(), text['sh_addr']
    ins, off, undecoded = [], 0, 0
    while off < len(d):
        got = False
        for i in md.disasm(d[off:], base + off):
            ins.append(i)
            got = True
            off = i.address + i.size - base
        if not got:
            undecoded += 4
            off += 4
    fp = [i for i in ins if i.mnemonic.startswith('v') or i.mnemonic in ('fmrx', 'fmxr', 'mcr', 'mrc', 'cdp', 'ldc', 'stc')]
    # System call numbers. The wrapper is inlined: "mov r7, #n" ... "svc 0". v3: the compiler also uses r7 as an
    # ordinary register (for constants such as 0xAAAB), so two sets are taken:
    #   reach: every immediate moved into r7 that is still in r7 when an svc follows in the listing (walked forward to
    #          the next write to r7 or the end of the function). These are the numbers the library can pass.
    #   all_imm: every immediate ever moved into r7 (a superset; used to show the dump build never loads 181).
    # Every call actually made in the scenarios also went through Run.sys, which fails on any other number.
    def writes_r7(p):
        ops = p.op_str.replace(' ', '')
        if p.mnemonic.startswith(('pop', 'ldm')) and 'r7' in ops:
            return True
        return ops.split(',')[0] == 'r7' and not p.mnemonic.startswith(('cmp', 'cmn', 'tst', 'teq', 'str', 'push', 'b'))

    def imm_r7(p):
        ops = p.op_str.replace(' ', '')
        return int(ops.split('#')[1], 0) if p.mnemonic in ('mov', 'movw') and ops.startswith('r7,#') else None

    all_imm = {imm_r7(p) for p in ins} - {None}
    calls = set()
    for k, p in enumerate(ins):
        v = imm_r7(p)
        if v is None:
            continue
        for q in ins[k + 1:k + 400]:
            if q.mnemonic == 'svc':
                calls.add(v)
                break
            ops = q.op_str.replace(' ', '')
            if writes_r7(q) or (q.mnemonic in ('bx', 'pop') and ('lr' in ops or 'pc' in ops)):
                break
    # "undecoded" words are the literal pools between functions (ARM state keeps constants next to the code)
    return {'needed': needed, 'undefined': undefined, 'insns': len(ins), 'undecoded': undecoded, 'fp_simd': len(fp), 'syscalls': calls,
            'r7_immediates': all_imm,
            'svc': sum(1 for i in ins if i.mnemonic == 'svc')}


def cam_from(m, system='59.94'):
    cam = Camera(system=system)
    cam.mem[:] = m
    return cam


if __name__ == '__main__':
    main()
