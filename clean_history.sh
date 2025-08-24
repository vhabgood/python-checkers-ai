#!/bin/bash

# --- Safety Check ---
# Ensure the user has made a backup.
echo "WARNING: This script will rewrite your repository's history."
echo "It is strongly recommended to make a backup of your project folder before proceeding."
read -p "Have you made a backup? (y/n) " -n 1 -r
echo    # move to a new line
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Aborted. Please make a backup and run the script again."
    exit 1
fi

# --- Main Script ---
echo "Starting history cleanup..."

# This command goes through every commit in your history and removes
# any file located in the 'logs/' directory.
git filter-branch --force --index-filter \
'git rm --cached --ignore-unmatch -r logs/' \
--prune-empty --tag-name-filter cat -- --all

echo "Local repository history has been cleaned."
echo "---"
echo "Next steps:"
echo "1. Add 'logs/' to your .gitignore file to prevent this from happening again."
echo "2. You must now force-push to update the remote repository on GitHub."
echo "   Run the following command:"
echo "   git push origin --force --all"
