#!/bin/bash

# Where is the extracted tarball or Git reporitory? Note that inside the
# repository, there's a subfolder also named "smlmp", which is the
# actual Python package. We should add the folder that includes the
# package to the PYTHONPATH, not the path of the package itself.
# This is unnecessary if you've already installed SMLMP to your Python
# installation.
# If you don't move this mda-wrapper.sh script from the examples/
# directory, the following line should set things up correctly:
export PYTHONPATH="$(dirname "${BASH_SOURCE}")"/..

# Alternatively, define it directly:
# export PYTHONPATH="$HOME/smlmp/:$PYTHONPATH"


# The following environment variables need to be preseved and shouldn't
# be modified in this script. Consult the SETUP documentation file for
# more information.
# 
# DOMAIN, LOCAL, MAIL_CONFIG, ORIGINAL_RECIPIENT, RECIPIENT, SENDER,
# EXTENSION

# Now, run the mail delivery agent as a module. (Do not run the file
# directly, it should be run properly as a Python module as it needs to
# import other modules in the package.)
python3 -m smlmp.mda
