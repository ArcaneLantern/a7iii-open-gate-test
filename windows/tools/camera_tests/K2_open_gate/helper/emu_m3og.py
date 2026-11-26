"""Run the built kit-2 helper libraries (32-bit ARM code) in Unicorn against a model camera, and check every level.

    python -I -B emu_m3og.py                 all scenarios against the real 4.04 av-cam.bin (a7m3_map/work/extracted)
    python -I -B emu_m3og.py --show dump     print the dump's result text

The model camera: physical memory with av-cam.bin at 0x035C6000 (its reservation up to 0x048C6000 zero-filled) and a
kernel-log ring at 0x035A5000; /dev/mem served by pread64/pwrite64; a small /proc and /sys; /tmp_network (RAM tmpfs) and /tmp/jiritsu.
The library is loaded as the dynamic linker would (PT_LOAD segments, R_ARM_RELATIVE relocations) and its DT_INIT_ARRAY
entries are called. Every system call the library makes is handled here; any other one fails the run.
"""
import hashlib
import io
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
DESIGN = ROOT / 'modding' / 'designs' / 'og_m3_v1.json'
LIBS = {n: HERE / ('libJit_m3og_%s.so' % n) for n in ('dump', 'test1', 'test2', 'putback')}

BASE, STACK, STACK_SZ, RET = 0x10000000, 0x7E000000, 0x100000, 0x7F000000
AV_PHYS, AV_END, KLOG_PHYS, KLOG_LEN = 0x035C6000, 0x048C6000, 0x035A5000, 0x20000
EEXIST, ENOENT, EBADF, EFAULT, ENOTDIR = 17, 2, 9, 14, 20


class Camera:
    """The model camera's memory and files."""

    def __init__(self, tmpfs=True, devmem=True):
        img = AVCAM.read_bytes()
        self.mem = bytearray(KLOG_LEN) + bytearray(AV_PHYS - KLOG_PHYS - KLOG_LEN) + bytearray(img) + bytearray(AV_END - AV_PHYS - len(img))
        self.mem_base = KLOG_PHYS
        klog = (b'<6>[    0.000000] Booting Linux on physical CPU 0\n<6>[    1.234567] wlan0: address 12:34:56:ab:cd:ef\n'
                b'<4>[    2.000000] liro: resume (WBI)\n')
        self.mem[0:len(klog)] = klog
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
    design = __import__('json').loads(DESIGN.read_text())
    stock = Camera().mem
    blocks = [(int(b['va'], 16) - 0x60000000, b['len']) for b in design['blocks']]

    def diff(m):
        return [i for i in range(len(m)) if m[i] != stock[i]]

    def in_blocks(offs):
        return all(any(p <= o + KLOG_PHYS < p + n for p, n in blocks) for o in offs)

    results = []

    def check(cond, what):
        results.append((bool(cond), what))
        print('%-4s %s' % ('pass' if cond else 'FAIL', what))

    if '--show' in sys.argv:
        _r, text = run(sys.argv[sys.argv.index('--show') + 1], Camera())
        print(text)
        return

    # 1. dump on a stock camera
    cam = Camera()
    r, t = run('dump', cam)
    check(not r.bad, 'dump: runs to the end (%s)' % (r.bad or 'ok'))
    check('VERDICT READY (stock)' in t and t.count('SAME as the 4.04 file') == 3 and t.count('  matches 4.04') == 16,
          'dump: LIRO header + 2 code ranges SAME, 16 image pages reported, verdict READY (stock)')
    check(not cam.writes and diff(cam.mem) == [], 'dump: memory untouched, no pwrite')
    check('0123456789abcdef' not in t and 'not copied by m3og' in t, 'dump: the cpuinfo Serial line is not copied')
    check('12:34:56:ab:cd:ef' not in t and 'xx:xx:xx:xx:xx:xx' in t and 'liro: resume (WBI)' in t, 'dump: kernel log copied as text, MAC address blanked')
    check('== dir /sys/module/liro/parameters' in t and '= 0x035c6000' in t, 'dump: liro parameters listed with values')
    check(t.count('== mem ') == 11 + 3 and t.rstrip().split('\n')[-1].startswith('== done'), 'dump: 14 memory ranges and the done line')
    check(list(cam.created) == ['/tmp_network/m3og_result.txt'], 'dump: result on /tmp_network (RAM)')
    # 1b. the first camera run: the first image pages hold live data (three runs, three hashes). v2 reports them and goes on
    cam = Camera()
    for o in (0x200, 0x1004):
        cam.mem[AV_PHYS - KLOG_PHYS + o] ^= 0x5A
    r, t = run('dump', cam)
    check('VERDICT READY (stock)' in t and t.count('differs from 4.04 (live data, not required)') == 2 and t.count('== mem image_page') == 2,
          'live data in image pages 0 and 1: dump READY (stock), both pages reported and copied out')
    r, t = run('test2', cam_from(bytes(cam.mem)))
    check('DONE: ' in t and 'READY (test 2 applied)' in t, 'live data in image pages 0 and 1: test2 DONE (the v1 refusal is gone)')
    # 2. test 1 on stock
    cam = Camera()
    r, t = run('test1', cam)
    d = diff(cam.mem)
    sites = sorted(int(s['va'], 16) - 0x60000000 - KLOG_PHYS for s in design['sensor_sites'])
    check(not r.bad and 'DONE: ' in t and 'READY (test 1 applied)' in t, 'test1: DONE, then READY (test 1 applied)')
    check(d == sites and all(cam.mem[o] == int(s, 16) for o, s in zip(sites, [x['new'] for x in sorted(design['sensor_sites'], key=lambda x: x['va'])])),
          'test1: exactly the 7 sensor bytes changed, to the design values')
    m1 = bytes(cam.mem)
    # 3. test 2 on top of test 1, then on stock
    r, t = run('test2', cam_from(m1))
    check(not r.bad and 'DONE: ' in t and 'READY (test 2 applied)' in t, 'test2 after test1: DONE, READY (test 2 applied)')
    cam = Camera()
    r, t = run('test2', cam)
    d2 = diff(cam.mem)
    nwords = sum(len(v) for v in design['records'].values())
    check(not r.bad and 'READY (test 2 applied)' in t and in_blocks(d2) and set(sites) <= set(d2), 'test2 on stock: DONE; changes only inside the 3 blocks')
    words_changed = len({o & ~1 for o in d2 if o not in sites})
    check(words_changed == nwords, 'test2: %d record words changed (design: %d)' % (words_changed, nwords))
    m2 = bytes(cam.mem)
    for va in design['records']:
        base = int(va, 16) - 0x60000000 - KLOG_PHYS
        ok = all(struct.unpack_from('<H', m2, base + 2 * w['word'])[0] == w['new'] for w in design['records'][va])
        check(ok, 'test2: record %s words hold the design values (step %d)' % (va, [w['new'] for w in design['records'][va] if w['word'] == 263][0]))
    # 4. test 1 over test 2 refuses
    cam = cam_from(m2)
    r, t = run('test1', cam)
    check(not r.bad and 'run the put-back first' in t and not cam.writes and bytes(cam.mem) == m2, 'test1 over test2: NOT DONE, nothing written')
    # 5. put back
    for name, m in (('test 2', m2), ('test 1', m1)):
        cam = cam_from(m)
        r, t = run('putback', cam)
        check(not r.bad and 'DONE: ' in t and 'READY (stock)' in t and bytes(cam.mem) == bytes(stock), 'putback after %s: memory equals 4.04 again' % name)
    cam = Camera()
    r, t = run('putback', cam)
    check('NOTHING TO DO' in t and not cam.writes, 'putback on stock: NOTHING TO DO, no write')
    cam = cam_from(m2)
    r, t = run('dump', cam)
    check('VERDICT READY (test 2 applied)' in t, 'dump after test 2: READY (test 2 applied)')
    # 6. identity differs -> nothing written, nothing more read
    cam = Camera()
    cam.mem[0x637B4000 - 0x60000000 - KLOG_PHYS] ^= 0xFF
    r, t = run('test2', cam)
    check(not r.bad and 'DIFFERS from the 4.04 file' in t and 'NOT DONE: av-cam identity' in t and not cam.writes, 'required code range differs: NOT DONE, no write')
    cam = Camera()
    cam.mem[0x637B4000 - 0x60000000 - KLOG_PHYS] ^= 0xFF
    r, t = run('dump', cam)
    check('VERDICT NOT READY' in t and t.count('== mem ') == 14 and '== blocks' in t, 'required code range differs: the dump still reads the blocks and tables')
    cam = Camera()
    cam.mem[AV_PHYS + 4 - KLOG_PHYS] ^= 1
    r, t = run('dump', cam)
    check('VERDICT NOT READY' in t and '== mem ' not in t, 'LIRO header differs: dump reads no av-cam tables')
    # 7. a block byte that is neither stock nor target
    cam = Camera()
    o = int(design['blocks'][1]['va'], 16) - 0x60000000 - KLOG_PHYS + 0x100
    cam.mem[o] ^= 0x5A
    r, t = run('test2', cam)
    check('NOT DONE: block fe_rec_0a' in t and not cam.writes, 'foreign byte in a block: NOT DONE, no write')
    # 8. a write fails part-way -> everything written is put back
    cam = Camera()
    cam.fail_write_at = 5
    r, t = run('test2', cam)
    check(not r.bad and 'putting back' in t and 'everything written was put back' in t and bytes(cam.mem) == bytes(stock), 'write failure: rolled back, memory equals 4.04')
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
        check(facts['syscalls'] <= allowed and (181 in facts['syscalls']) == (n != 'dump'),
              '%s: %d svc sites, r7 only ever %s%s' % (p.name, facts['svc'], sorted(facts['syscalls']), '' if n != 'dump' else ' (no pwrite64 in the read-only build)'))
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
    # The svc sites are inlined and the compiler keeps r7 (the system call number) set once per function, so every
    # immediate ever moved into r7 is collected: a superset of the system call numbers the library can make.
    calls = {int(i.op_str.split('#')[1], 0) for i in ins if i.mnemonic in ('mov', 'movw') and i.op_str.startswith('r7, #')}
    # "undecoded" words are the literal pools between functions (ARM state keeps constants next to the code)
    return {'needed': needed, 'undefined': undefined, 'insns': len(ins), 'undecoded': undecoded, 'fp_simd': len(fp), 'syscalls': calls,
            'svc': sum(1 for i in ins if i.mnemonic == 'svc')}


def cam_from(m):
    cam = Camera()
    cam.mem[:] = m
    return cam


if __name__ == '__main__':
    main()
