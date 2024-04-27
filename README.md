# cosmicweb-music

A script to download [MUSIC](https://github.com/cosmo-sims/music) initial conditions for zoom-in cosmological simulations from the [cosmICweb service](https://cosmicweb.eu).

## Installation

```bash
pip install cosmicweb-music
```

## Usage
```text
Usage: cosmicweb-music [OPTIONS] COMMAND [ARGS]...

Options:
  --url TEXT              overwrite URL of the cosmICweb server
  --output-path DIR_PATH  Download target for IC files. If downloading
                          publication, will create a subfolder with the name
                          of the publication
  --common-directory      store all config files in the same directory instead
                          of individual directories for each halo
  --attempts INTEGER      number of attempts to download ellipsoids
  --verbose
  --help                  Show this message and exit.

Commands:
  collection   Download shared ICs using the collection UUID
  get          Download ICs using a target UUID generated on cosmICweb
  publication  Download published ICs using the publication name
```
### Examples
```bash
cosmicweb-music publication agora-halos
```
```bash
cosmicweb-music get f5399734-ad67-432b-ba4d-61bc2088136a
```
```bash
cosmicweb-music collection c30de0f3-ab4d-48ad-aa26-f20bb4b70bbd
```
