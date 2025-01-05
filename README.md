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
├── cache           # cache for packages
├── packages        # build repository for gn package description
├── scripts         # scripts for build
├── toolchains      # support build toolchains
├── package.gni     # imported by BUILDCONFIG.gn
└── README.md       # this file
```

## usage
see [mds_demo](https://github.com/wpchom/mds_demo) for example.
