{
  description = "Bare-bones dev environment for red-teaming-openai-gpt-oss-20b";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
              python3Packages.jsonschema
              python3Packages.openai
              python3Packages.python-dotenv
          ];
        };
      }
    );
}
