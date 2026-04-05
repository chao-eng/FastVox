#!/bin/bash
# 自动清理残留的共享内存块

PLATFORM=$(uname)

if [ "$PLATFORM" == "Linux" ]; then
    echo "Cleaning up Linux SHM residues (/dev/shm/fastvox_*)..."
    rm -f /dev/shm/fastvox_*
elif [ "$PLATFORM" == "Darwin" ]; then
    echo "Cleaning up macOS SHM residues via Python helper..."
    # macOS 不通过物理文件管理 SHM，需通过 multiprocessing.shared_memory 逐一尝试 unlink
    python3 <<EOF
from multiprocessing import shared_memory
import sys

shm_names = ["fastvox_shm_main"]
for name in shm_names:
    try:
        shm = shared_memory.SharedMemory(name=name)
        shm.close()
        shm.unlink()
        print(f"Successfully unlinked SHM: {name}")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Error unlinking {name}: {e}")
EOF
fi

echo "SHM Cleanup complete."
