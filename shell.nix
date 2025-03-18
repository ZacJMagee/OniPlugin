# shell.nix for setting up a Python development environment with dependencies
{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell rec {
  name = "account-updater-env";

  buildInputs = [
    pkgs.python3
    pkgs.python3Packages.pip
    pkgs.python3Packages.setuptools
    pkgs.python3Packages.pyinstaller
  ];

  # If you want to install your Python dependencies locally
  shellHook = ''
    export PYTHONPATH=${pkgs.python3.sitePackages}
    echo "You are now in the account-updater environment"
  '';
}

