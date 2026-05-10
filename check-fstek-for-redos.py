#!/usr/bin/python3

import os
import subprocess

TAB_VALUES = (
    40,
    20,
    20,
    20,
    50
)

#  опция: референсное значение, комментарий
sysctl_dict = {
    "kernel.dmesg_restrict": ("1", None),
    "kernel.kptr_restrict": ("2", None),
    "kernel.randomize_va_space": ("2", "kernel:CONFIG_COMPAT_BRK=n"),
    "kernel.yama.ptrace_scope": ("3", None),
    "kernel.kexec_load_disabled": ("1", None),
    "kernel.unprivileged_bpf_disabled": ("2", None),
    "kernel.perf_event_paranoid": ("3", None),
    "vm.unprivileged_userfaultfd": ("0", None),
    "vm.mmap_min_addr": ("4096", "boot:CONFIG_DEFAULT_MMAP_MIN_ADDR=4096"),
    "fs.protected_symlinks": ("1", None),
    "fs.protected_hardlinks": ("1", None),
    "fs.protected_fifos": ("2", None),
    "fs.protected_regular": ("2", None),
    "fs.suid_dumpable": ("0", None),
    "user.max_user_namespaces": ("0", None),
    "dev.tty.ldisc_autoload": ("0", "kernel:CONFIG_LDISC_AUTOLOAD=n"),
    "net.core.bpf_jit_harden": ("2", None)
}
sudo_calls = [
    "fs.protected_symlinks",
    "fs.protected_hardlinks",
    "fs.protected_fifos",
    "fs.protected_regular",
    "net.core.bpf_jit_harden"
]
cmdline_dict = {
    "init_on_alloc": (None, "kernel:CONFIG_INIT_ON_ALLOC_DEFAULT_ON=y"),
    "slab_nomerge": (None, "kernel:CONFIG_SLAB_MERGE_DEFAULT=n"),
    "iommu": ("force", None),
    "iommu.strict": ("1", None),
    "iommu.passthrough": ("0", None),
    "randomize_kstack_offset": ("1", "kernel:CONFIG_RANDOMIZE_KSTACK_OFFSET_DEFAULT=y"),
    "mitigations": ("auto,nosmt", None),
    "vsyscall": ("none", "kernel:CONFIG_LEGACY_VSYSCALL_NONE=y"),
    "debugfs": ("no-mount", "kernel:CONFIG_DEBUG_FS_DISALLOW_MOUNT=y"),
    "tsx": ("off", "kernel:CONFIG_X86_INTEL_TSX_MODE_OFF=y")
}

kernel_dict = {
    "CONFIG_INIT_ON_ALLOC_DEFAULT_ON": ("y", "boot:init_on_alloc"),
    "CONFIG_SLAB_MERGE_DEFAULT": ("n", "boot:slab_nomerge"),
    "CONFIG_RANDOMIZE_KSTACK_OFFSET_DEFAULT": ("y", "boot:randomize_kstack_offset=1"),
    "CONFIG_LEGACY_VSYSCALL_NONE": ("y", "boot:vsyscall=none"),
    "CONFIG_LDISC_AUTOLOAD": ("n", "sysctl:dev.tty.ldisc_autoload=0"),
    "CONFIG_X86_INTEL_TSX_MODE_OFF": ("y", "boot:tsx=off"),
    "CONFIG_COMPAT_BRK": ("n", "sysctl:kernel.randomize_va_space=2"),
    "CONFIG_DEBUG_FS_DISALLOW_MOUNT": ("y", "boot:debugfs=no-mount"),
    "CONFIG_DEBUG_FS": ("n", None)
}


def print_header(header: str, length=150):
    print("=" * length)
    print(
        f"{header: ^{TAB_VALUES[0]}}"
        f"{'Current' : ^{TAB_VALUES[1]}}"
        f"{'Recommended value' : ^{TAB_VALUES[2]}}"
        f"{'Check result' : ^{TAB_VALUES[3]}}"
        f"{'Alternative' : ^{TAB_VALUES[4]}}")
    print("=" * length)


def sanitize_str(input_str) -> str:
    return "" if input_str is None else str(input_str)


def compare_sysctl():
    print_header('Sysctl Option')

    for key, ref_val in sysctl_dict.items():
        ret = subprocess.run(['/sbin/sysctl', key],
                             stderr=subprocess.DEVNULL,
                             stdout=subprocess.PIPE).stdout.decode('utf-8')
        if (os.geteuid() != 0) and (key in sudo_calls) or not ret:
            cur_val, cur_result = "unknown", "unknown"
        else:
            cmd, cur_val = ret.split()[0], ret.split()[2]
            cur_result = "OK" if cur_val == ref_val[0] else "FAIL"
        print(
            f"{key:<{TAB_VALUES[0]}}"
            f"{cur_val:^{TAB_VALUES[1]}}"
            f"{ref_val[0]:^{TAB_VALUES[2]}}"
            f"{cur_result:^{TAB_VALUES[3]}}"
            f"{ref_val[1] if ref_val[1] else '':<{TAB_VALUES[4]}}")
    print()


def compare_cmdline():
    print_header('Boot Option')
    ret = subprocess.run(['cat', '/proc/cmdline'], stdout=subprocess.PIPE).stdout.decode('utf-8').split()
    ret_dict = {}
    for item in ret:
        split_item = item.split('=')
        ret_dict[split_item[0]] = split_item[1] if len(split_item) == 2 else None
    for key, ref_val in cmdline_dict.items():
        if key in ret_dict.keys():
            cur_result = "OK" if ret_dict[key] == ref_val[0] else "FAIL"
            print(
                f"{sanitize_str(key):<{TAB_VALUES[0]}}"
                f"{sanitize_str(ret_dict[key]):^{TAB_VALUES[1]}}"
                f"{sanitize_str(ref_val[0]):^{TAB_VALUES[2]}}"
                f"{sanitize_str(cur_result):^{TAB_VALUES[3]}}"
                f"{sanitize_str(ref_val[1]):<{TAB_VALUES[4]}}")
        else:
            ref_val_tmp = ref_val[0] if ref_val[0] else "no value"
            print(
                f"{sanitize_str(key):<{TAB_VALUES[0]}}"
                f"{'not present':^{TAB_VALUES[1]}}"
                f"{sanitize_str(ref_val_tmp):^{TAB_VALUES[2]}}"
                f"{'FAIL':^{TAB_VALUES[3]}}"
                f"{sanitize_str(ref_val[1]):<{TAB_VALUES[4]}}")
    print()


def compare_config():
    print_header('Kernel Option')
    uname = subprocess.run(['uname', '-r'], stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
    config_path = os.path.expanduser(f"/boot/config-{uname}")
    if not os.path.exists(config_path):
        print("config not found")
        return
    for key, ref_val in kernel_dict.items():
        ret = subprocess.run(['grep', '-w', key, config_path],
                             stdout=subprocess.PIPE).stdout.decode('utf-8').split()
        if not ret:
            print(f"{key:<{TAB_VALUES[0]}}"
                  f"{'None':^{TAB_VALUES[1]}}"
                  f"{ref_val[0]:^{TAB_VALUES[2]}}"
                  f"{'FAIL':^{TAB_VALUES[3]}}"
                  f"{ref_val[1] if ref_val[1] else '':<{TAB_VALUES[4]}}")
            continue
        elif len(ret) == 1:
            split_ret = ret[0].split('=')
            cur_result = "OK" if split_ret[1] == ref_val[0] else "FAIL"
            print(
                f"{key:<{TAB_VALUES[0]}}"
                f"{split_ret[1]:^{TAB_VALUES[1]}}"
                f"{ref_val[0]:^{TAB_VALUES[2]}}"
                f"{cur_result:^{TAB_VALUES[3]}}"
                f"{ref_val[1] if ref_val[1] else '':<{TAB_VALUES[4]}}")
        else:
            print(
                f"{key:<{TAB_VALUES[0]}}"
                f"{'is not set':^{TAB_VALUES[1]}}"
                f"{ref_val[0]:^{TAB_VALUES[2]}}"
                f"{'FAIL':^{TAB_VALUES[3]}}"
                f"{ref_val[1] if ref_val[1] else '':<{TAB_VALUES[4]}}")
    print()


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Без прав администратора информация будет неполной")
    compare_cmdline()
    compare_sysctl()
    compare_config()
