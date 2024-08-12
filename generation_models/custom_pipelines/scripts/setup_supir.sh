#!/bin/bash
cd generation_models/custom_pipelines
git clone https://github.com/vietbeu/SUPIR.git && cd SUPIR && git checkout cb360bc2757b409ffa2001db2c0f82a51ace5039
cd ../../..

CLIP_URL="https://huggingface.co/openai/clip-vit-large-patch14"
CLIP_DIR="checkpoints/SUPIR/clip-vit-large-patch14"
if [ ! -d "$CLIP_DIR" ]; then
  echo "CLIP directory does not exist. Cloning the repository..."
  git clone "$CLIP_URL" "$CLIP_DIR"
else
  echo "CLIP directory already exists. Skipping clone."
fi

# get LFS sha256 hash
get_lfs_sha256() {
    local repo_url=$1
    local file_path=$2
    
    # Clone only the LFS pointers without downloading the actual files
    tmp_dir=$(mktemp -d)
    git clone --no-checkout --filter=blob:none $repo_url $tmp_dir
    
    cd $tmp_dir
    git checkout HEAD -- $file_path
    
    # Extract the SHA256 from the LFS pointer file
    sha256=$(cat $file_path | grep -oP '(?<=sha256:)[a-f0-9]{64}')
    
    cd - > /dev/null
    rm -rf $tmp_dir
    
    echo $sha256
}

# download file if it doesn't exist or has wrong hash
download_file() {
    local file=$1
    local url=$2
    local repo_url=$3
    local file_path=$4
    local temp_file="${file}.tmp"

    # Check if the file is a ZIP file
    if [[ "${file}" == *.zip ]]; then
        echo "ZIP file detected. Skipping checksum verification for ${file}."
        if [ ! -f "$file" ]; then
            wget -O "$file" "$url"
            echo "Downloaded ZIP file ${file}."
        else
            echo "ZIP file ${file} already exists. Skipping download."
        fi
        return
    fi

    expected_hash=$(get_lfs_sha256 $repo_url $file_path)

    if [ -f "$file" ]; then
        local_hash=$(sha256sum "$file" | awk '{print $1}')
        if [ "$local_hash" = "$expected_hash" ]; then
            echo "File $file exists and has correct hash. Skipping download."
            return
        else
            echo "File $file exists but has incorrect hash. Re-downloading."
        fi
    else
        echo "File $file does not exist. Downloading."
    fi

    dir_path=$(dirname "$temp_file")
    mkdir -p "$dir_path"
    wget -d -O "$temp_file" "$url"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to download file from $url" >&2
        exit 1
    else
        echo "File downloaded successfully."
    fi
    downloaded_hash=$(sha256sum "$temp_file" | awk '{print $1}')

    if [ "$downloaded_hash" = "$expected_hash" ]; then
        mv "$temp_file" "$file"
        echo "File $file downloaded successfully and verified."
    else
        echo "Downloaded file $file has incorrect hash. Please check the source and try again."
        rm "$temp_file"
        exit 1
    fi
}


download_file "checkpoints/SUPIR/CLIP-ViT-bigG-14-laion2B-39B-b160k/open_clip_pytorch_model.bin" \
              "https://huggingface.co/laion/CLIP-ViT-bigG-14-laion2B-39B-b160k/resolve/main/open_clip_pytorch_model.bin?download=true" \
              "https://huggingface.co/laion/CLIP-ViT-bigG-14-laion2B-39B-b160k" \
              "open_clip_pytorch_model.bin"

download_file "checkpoints/SUPIR/SUPIR_cache/SUPIR-v0Q.ckpt" \
              "https://huggingface.co/camenduru/SUPIR/resolve/main/SUPIR-v0Q.ckpt?download=true" \
              "https://huggingface.co/camenduru/SUPIR" \
              "SUPIR-v0Q.ckpt"

download_file "checkpoints/SUPIR/SDXL_lightning_cache/Juggernaut_RunDiffusionPhoto2_Lightning_4Steps.safetensors" \
              "https://huggingface.co/RunDiffusion/Juggernaut-XL-Lightning/resolve/main/Juggernaut_RunDiffusionPhoto2_Lightning_4Steps.safetensors?download=true" \
              "https://huggingface.co/RunDiffusion/Juggernaut-XL-Lightning" \
              "Juggernaut_RunDiffusionPhoto2_Lightning_4Steps.safetensors"

