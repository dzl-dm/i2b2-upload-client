#!/bin/bash
## Installer for DWH upload gui client

## User must have java, python available
java -version > /dev/null 2>&1 || (echo "Java not available" && exit 1)
python --version > /dev/null 2>&1 || (echo "Python not available" && exit 1)

## Install python libraries
if ! pip install -r pseudonym/src/requirements.txt > /dev/null 2>&1 ; then
    >&2 echo "Cannot use pip directly (system-wide), creating venv..."
    python -m venv ./.venv
    ./.venv/bin/pip install -r src/requirements.txt
fi

function find_bin_dir {
    ## Usually a linux type user has a directory which is used to look for executable commands. We try to use one which exists, otherwise we create it
    declare -a bin_dirs
    bin_dirs=($HOME/bin $HOME/.local/bin $HOME/.bin)
    path_dirs=($(echo $PATH | tr ':' ' '))
    for bin_dir in "${bin_dirs[@]}"; do
        if [[ " ${path_dirs[*]} " =~ [[:space:]]${bin_dir}[[:space:]] ]]; then
            [ -d "$bin_dir" ] || mkdir -p $bin_dir
            echo $bin_dir
            return 0
        fi
    done
    ## Else, create a local user bin directory and add to PATH
    new_bin_dir="$HOME/bin"
    export PATH=$new_bin_dir:$PATH
    echo "export PATH=$new_bin_dir:\$PATH" >> ~/.bashrc
    echo $new_bin_dir
}

# src_path="$(dirname $(readlink -f ${BASH_SOURCE[0]}))/src"
# bin_dir=$(find_bin_dir)
# ## Symlink into PATH
# [[ -L ${bin_dir}/dwh_client.sh ]] && rm ${bin_dir}/dwh_client.sh
# ln -s ${src_path}/dwh_client.sh ${bin_dir}/dwh_client.sh

echo ""
echo "DWH Uploader Client installation complete"
echo -e "You can now run the client with:\n./dwh_client.sh"
echo ""
