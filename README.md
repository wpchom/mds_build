# mds_build

mds_build is a python script to build with 'gn' and 'ninja' for sources.

## requires
- python3
- git
- gn
- ninja

# directories
```
.
├── README.md       # this file
├── package.gni     # imported by BUILDCONFIG.gn
├── pkgs            # store build package/resource/binary
├── repos           # build repository for gn package description
├── scripts         # some build scripts
└── toolchains      # support build toolchains
```

## usage
see [mds_demo](https://github.com/wpchom/mds_demo) for example.
