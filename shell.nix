{ pkgs ? import <nixpkgs> {} }: let
  pythonPackages = pkgs.python3Packages;
  
  # Latest pyairtable package
  pyairtable = pythonPackages.buildPythonPackage rec {
    pname = "pyairtable";
    version = "2.1.0.post1";
    format = "setuptools";
    src = pythonPackages.fetchPypi {
      inherit pname version;
      sha256 = "sha256-5YgknmjPM43NypkIU37RbVoirnI0XskwAisjC6luX4Q=";  # Update this with correct hash

    };
    propagatedBuildInputs = with pythonPackages; [requests inflection pydantic];
    doCheck = false;
  };
  
  # Python environment with all required packages
  pythonWithPackages = pkgs.python3.withPackages (ps: with ps; [
    # Core packages
    pyyaml
    pyairtable
    
    # Google API related packages
    google-auth-oauthlib
    google-auth-httplib2
    google-api-python-client
    requests
    
    # Data processing
    pandas
    numpy
    
    # Development tools
    python-lsp-server
    python-dotenv
    ipython
    
    # Optional extras for file handling
    pillow  # For image processing
  ]);

in pkgs.mkShell {
  buildInputs = with pkgs; [
    zsh
    pythonWithPackages
    git
    curl
    jq
  ];
  
  shellHook = ''
    export ZDOTDIR="$HOME"
    export PYTHONPATH="$PWD:$PYTHONPATH"
    echo "Instagram Content Manager Development Environment"
    echo "Python version: $(python --version)"
    echo "Python development environment ready!"
    
    # Create basic directory structure
    mkdir -p downloaded_media
    
    # Launch zsh
    exec zsh
  '';
}
