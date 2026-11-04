"""Build against an installed STM32CubeL4 (no vendor code copied into this repo)."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--cube', type=Path, required=True, help='STM32CubeL4 root, version 1.18.1 used')
    p.add_argument('--gcc-bin', type=Path, help='directory containing arm-none-eabi-gcc')
    args = p.parse_args()
    gcc = str(args.gcc_bin / 'arm-none-eabi-gcc') if args.gcc_bin else shutil.which('arm-none-eabi-gcc')
    if not gcc:
        p.error('arm-none-eabi-gcc not found')
    hal = args.cube / 'Drivers/STM32L4xx_HAL_Driver'
    cmsis = args.cube / 'Drivers/CMSIS'
    device = cmsis / 'Device/ST/STM32L4xx'
    startup = device / 'Source/Templates/gcc/startup_stm32l432xx.s'
    system = device / 'Source/Templates/system_stm32l4xx.c'
    names = ['hal', 'hal_cortex', 'hal_rcc', 'hal_rcc_ex', 'hal_pwr', 'hal_pwr_ex',
             'hal_gpio', 'hal_dma', 'hal_adc', 'hal_adc_ex', 'hal_flash', 'hal_flash_ex',
             'hal_tim', 'hal_tim_ex', 'hal_uart', 'hal_uart_ex', 'hal_sai', 'hal_sai_ex']
    sources = sorted((ROOT / 'src').glob('*.c')) + [system, startup]
    sources += [hal / 'Src' / f'stm32l4xx_{name}.c' for name in names]
    for src in sources:
        if not src.exists():
            p.error(f'missing dependency: {src}')
    out = ROOT / 'build'
    out.mkdir(exist_ok=True)
    common = ['-mcpu=cortex-m4', '-mthumb', '-mfpu=fpv4-sp-d16', '-mfloat-abi=hard',
              '-DSTM32L432xx', '-DUSE_HAL_DRIVER', '-O2', '-g3', '-ffunction-sections',
              '-fdata-sections', '-Wall', '-Wextra']
    includes = [ROOT / 'include', hal / 'Inc', cmsis / 'Include', device / 'Include']
    common += [f'-I{x}' for x in includes]
    objects = []
    for src in sources:
        obj = out / (src.stem + '.o')
        flags = ['-std=c11', '-Werror'] if src.parent == ROOT / 'src' else []
        subprocess.run([gcc, *common, *flags, '-c', str(src), '-o', str(obj)], check=True)
        objects.append(str(obj))
    elf = out / 'sonometro.elf'
    subprocess.run([gcc, *common, *objects, '-nostartfiles', '--specs=nano.specs', '--specs=nosys.specs',
                    '-T' + str(ROOT / 'stm32l432kc.ld'), '-Wl,--gc-sections',
                    '-Wl,--print-memory-usage', '-Wl,-Map=' + str(out / 'sonometro.map'),
                    '-Wl,--fatal-warnings', '-o', str(elf)], check=True)
    prefix = str(args.gcc_bin / 'arm-none-eabi-') if args.gcc_bin else 'arm-none-eabi-'
    subprocess.run([prefix + 'size', str(elf)], check=True)
    subprocess.run([prefix + 'objcopy', '-O', 'binary', str(elf), str(out / 'sonometro.bin')], check=True)
    manifest = {'compiler': subprocess.check_output([gcc, '--version'], text=True).splitlines()[0],
                'elf_sha256': hashlib.sha256(elf.read_bytes()).hexdigest(),
                'sources_sha256': {str(src): hashlib.sha256(src.read_bytes()).hexdigest() for src in sources}}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
