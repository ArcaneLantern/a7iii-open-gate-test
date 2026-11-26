#!/bin/bash
# Build the six A7 III kit-2 helper libraries (m3og.c, one per level) and print their SHA-256.
#   bash build_m3og.sh            -> libJit_m3og_{dump,test1,test2,test3,test4,putback}.so
# Target: 32-bit ARM (ARMv7-A, Cortex-A5 class, ARM state, soft-float calls, no unaligned access), the flags of the
# original A7S tools on the same platform family (A7s Claude tools/a7s_poke/build_and_test.sh), as a shared object with
# no imports and no libc. Needs zig (python -m ziglang, pinned 0.13.0).
# NO FP OR SIMD INSTRUCTIONS: the A7 III's own code is built for VFPv3-D16 without NEON (a7m3_map M3-F004) and whether
# its core has NEON is unknown. Plain -mcpu=cortex_a5 lets clang turn the copy loops into NEON (vld1/vst1 on d16-d31),
# which would be an undefined instruction there; "-neon-vfp2-vfp3-vfp4" removes every FP/SIMD instruction (emu_m3og.py
# checks the built files for any).
set -e
H="$(cd "$(dirname "$0")" && pwd)"
if [ -n "${ZIG_PYTHON:-}" ]; then PY="$ZIG_PYTHON"
elif [ -x "$H/../../../../a7iv_map/work/venv_zig/Scripts/python.exe" ]; then PY="$H/../../../../a7iv_map/work/venv_zig/Scripts/python.exe"
else PY="python3"; fi
cd "$H"
for pair in 1:dump 11:test1 21:test2 22:test3 23:test4 31:putback; do
  L="${pair%%:*}"; N="${pair##*:}"
  "$PY" -m ziglang cc -target arm-linux-gnueabi -mcpu=cortex_a5-neon-vfp2-vfp3-vfp4 -marm -mno-unaligned-access \
    -std=gnu11 -O1 -Wall -Wextra -Werror -fPIC -shared -nostdlib -ffreestanding -fno-builtin -fno-stack-protector \
    -fno-asynchronous-unwind-tables -fno-unwind-tables -fvisibility=hidden -fomit-frame-pointer \
    -Wl,-soname,libJit.so -Wl,--no-undefined -Wl,-z,now -Wl,--build-id=none -Wl,-z,max-page-size=4096 -g0 -s \
    -DLEVEL=$L m3og.c -o "libJit_m3og_$N.so"
done
for f in libJit_m3og_dump.so libJit_m3og_test1.so libJit_m3og_test2.so libJit_m3og_test3.so libJit_m3og_test4.so libJit_m3og_putback.so; do
  if command -v sha256sum >/dev/null 2>&1; then s=$(sha256sum "$f" | cut -d' ' -f1); else s=$(shasum -a 256 "$f" | cut -d' ' -f1); fi
  echo "$s $(wc -c < "$f" | tr -d ' ') $f"
done
