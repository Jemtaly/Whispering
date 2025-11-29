#!/bin/bash
# Debug script to show environment differences

echo "=========================================="
echo "Environment Diagnostics"
echo "=========================================="

# Check if running through run.sh or directly
echo -e "\n1. LD_LIBRARY_PATH:"
echo "${LD_LIBRARY_PATH:-<not set>}"

# Check for nvidia packages
echo -e "\n2. Installed nvidia packages:"
pip list | grep -i nvidia

# Check PyTorch's CUDA libraries location
echo -e "\n3. PyTorch CUDA libs:"
python -c "import torch; import os; print(f'PyTorch dir: {os.path.dirname(torch.__file__)}')"
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'cuDNN version: {torch.backends.cudnn.version()}')"

# Check for conflicting libraries
echo -e "\n4. Looking for libcudnn files:"
find ~/.cache -name "*cudnn*" 2>/dev/null | head -5
find .venv -name "*cudnn*" 2>/dev/null | head -5

echo -e "\n=========================================="
echo "Recommendation:"
echo "=========================================="
echo "If you see nvidia-cudnn* or nvidia-cublas* packages above,"
echo "they might be conflicting with PyTorch's bundled libraries."
echo ""
echo "Try uninstalling them:"
echo "  pip uninstall nvidia-cudnn-cu12 nvidia-cudnn-cu11 nvidia-cublas-cu12 nvidia-cublas-cu11 -y"
echo "=========================================="
