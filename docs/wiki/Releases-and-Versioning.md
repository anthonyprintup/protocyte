# Releases and Versioning

Protocyte currently reports version `0.1.0` and remains pre-1.0. “V1” describes
the first complete user-experience and documentation milestone; it is not a
promise of a stable `1.0.0` compatibility boundary.

## Choosing a version

Pin an immutable full commit SHA before the first release:

```cmake
FetchContent_Declare(
    protocyte
    GIT_REPOSITORY https://github.com/anthonyprintup/protocyte.git
    GIT_TAG 9bae6fe8bf78a47a6356dc1fdc1e0ab8baa97d14
    GIT_SHALLOW FALSE
)
```

After a release exists, prefer its real immutable tag. Do not copy placeholder
tags from examples or assume an unpublished asset exists.

## Planned release assets

No tag or GitHub release has been published yet. The release workflow is
prepared to publish:

- `protocyte-X.Y.Z-py3-none-any.whl` — Python generator wheel;
- `protocyte-X.Y.Z.tar.gz` — Python source distribution;
- `protocyte-X.Y.Z-cmake-prefix.tar.gz` — relocatable installed CMake prefix.

The Python artifacts require Python 3.12 or newer. The CMake prefix contains
the CMake package, runtime headers, and installable generator project, but not
Python itself.

Prerelease tags such as `vX.Y.Z-rcN` use normalized Python filenames containing
`X.Y.ZrcN`; the CMake prefix archive retains `X.Y.Z-rcN`.

## Updating Protocyte

When changing a pin:

1. review the release notes or commit range;
2. update the immutable reference;
3. regenerate any checked output;
4. rebuild every generated target;
5. run the downstream test suite;
6. review generated API and runtime configuration changes.

Until `1.0.0`, compatibility shims are not guaranteed.

## Maintainers

Release administration and security prerequisites live in the
[Maintainer Release Guide](Maintainer-Release-Guide).
