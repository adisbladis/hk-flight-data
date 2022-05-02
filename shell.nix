let
  pkgs = import <nixpkgs> {};
  inherit (pkgs) lib stdenv;

  poetryEnv = pkgs.poetry2nix.mkPoetryEnv {
    projectDir = ./.;
    preferWheels = true;
    overrides = pkgs.poetry2nix.overrides.withDefaults(self: super: {

      pandas = super.pandas.overridePythonAttrs(old: {

        buildInputs = old.buildInputs or [ ] ++ lib.optional stdenv.isDarwin pkgs.libcxx;

          # Doesn't work with -Werror,-Wunused-command-line-argument
          # https://github.com/NixOS/nixpkgs/issues/39687
          hardeningDisable = lib.optional stdenv.cc.isClang "strictoverflow";

          # For OSX, we need to add a dependency on libcxx, which provides
          # `complex.h` and other libraries that pandas depends on to build.
          postPatch = lib.optionalString stdenv.isDarwin ''
            cpp_sdk="${lib.getDev pkgs.libcxx}/include/c++/v1";
            echo "Adding $cpp_sdk to the setup.py common_include variable"
            substituteInPlace setup.py \
              --replace "['pandas/src/klib', 'pandas/src']" \
                        "['pandas/src/klib', 'pandas/src', '$cpp_sdk']"
                      '';


          enableParallelBuilding = true;
      });

    });
  };

in
pkgs.mkShell {
  packages = [
    pkgs.poetry
    pkgs.openjdk
    poetryEnv
  ];
}
