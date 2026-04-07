{
  description = "glint - Image filter pipeline with LLM and Vision support";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          numpy
          pillow
          httpx
          pytest
          fastapi
          uvicorn
          python-multipart
          jinja2
          black
          ruff
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [ pythonEnv ];
          
          shellHook = ''
            export PYTHONPATH=$PYTHONPATH:$(pwd)
            echo "glint devShell active"
            alias glint="python -m glint.cli"
          '';
        };

        packages.default = pkgs.python3Packages.buildPythonApplication {
          pname = "glint";
          version = "0.2.1";
          src = ./.;
          pyproject = true;
          
          build-system = with pkgs.python3Packages; [ setuptools wheel ];
          
          propagatedBuildInputs = with pkgs.python3Packages; [
            numpy
            pillow
            httpx
            fastapi
            uvicorn
            python-multipart
            jinja2
          ];

          meta = with pkgs.lib; {
            description = "Image filter pipeline with LLM support";
            license = licenses.mit;
          };
        };
      });
}