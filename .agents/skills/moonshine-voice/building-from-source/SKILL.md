---
name: building-from-source
description: Building the Moonshine Voice core library from source with CMake, building the language bindings, and porting the library to a new platform. Use when no prebuilt binary fits the target, when changing the C++ core, or when bringing Moonshine to a new OS, architecture or language binding.
---

# Building from Source

Build the Moonshine Voice core library yourself: to debug into its internals, add instrumentation, customize it, or bring it to a platform or language with no prebuilt package. Prebuilt packages for the supported platforms are in the [root skill](../SKILL.md).

## Before you build

Large model and TTS binaries are **not** in git. Fetch them from the CDN (or the [Hugging Face mirror](https://huggingface.co/moonshine-ai/moonshine-voice-assets)) before running the core tests or doing offline TTS work:

```bash
scripts/fetch-voice-assets.sh all
```

A few compile-time embeds and ONNX Runtime prebuilts still use Git LFS. Install git-lfs and run `git lfs install` before cloning, or `git lfs pull` in an existing clone. Without it, compiling embedded sources such as `community1_cpp_annote_embedded.cpp` fails with errors like `'version' does not name a type`, because the LFS pointers are left as text.

## Build the core with CMake

The core engine is in the repo's `core` folder: C++ with a C interface. CMake builds it on every platform:

```bash
cd core
mkdir -p build
cd build
cmake ..
cmake --build .
```

The resulting executables are unit tests and expect to run from the `test-assets` folder. Build and test in one step with [`scripts/test-core.sh`](https://github.com/moonshine-ai/moonshine/blob/main/scripts/test-core.sh) (or [`scripts/test-core.bat`](https://github.com/moonshine-ai/moonshine/blob/main/scripts/test-core.bat) on Windows). All tests should compile and run without errors.

The same build directory also produces the `./benchmark` tool, built with `cmake --build . --config Release` (see [choosing-a-model](../choosing-a-model/SKILL.md)).

## Language bindings

- [`scripts/build-all-platforms.sh`](https://github.com/moonshine-ai/moonshine/blob/main/scripts/build-all-platforms.sh) is the release script. It builds every artifact uploaded to the package managers, so use it as the example of how to build each platform.
- Each binding is a layer on top of the C interface that adds idiomatic APIs and the platform's event system. They live under [`language-bindings/`](https://github.com/moonshine-ai/moonshine/tree/main/language-bindings): [`python`](https://github.com/moonshine-ai/moonshine/blob/main/language-bindings/python/), [`android`](https://github.com/moonshine-ai/moonshine/blob/main/language-bindings/android/), [`swift`](https://github.com/moonshine-ai/moonshine/blob/main/language-bindings/swift/) (iOS and macOS).
- Branches: `main` always matches the most recently published binaries; development happens on a `dev-v<version>` candidate branch ([`docs/release-process.md`](https://github.com/moonshine-ai/moonshine/blob/main/docs/release-process.md)).

## Porting to a new platform

1. Try the CMake build above on the target system.
2. The only major dependency is [ONNX Runtime](https://github.com/microsoft/onnxruntime). Prebuilt libraries for supported systems are in [`core/third-party/onnxruntime/lib/`](https://github.com/moonshine-ai/moonshine/blob/main/core/third-party/onnxruntime/lib/). For anything else, find or build your own.

## Calling from an unsupported language

Bind to the C interface, [`core/moonshine-c-api.h`](https://github.com/moonshine-ai/moonshine/blob/main/core/moonshine-c-api.h). Most languages can call C functions; use the existing bindings as guides. Every function and struct is summarized in [c-api](../reference/c-api/SKILL.md).

## Source docs

Verbatim copies, for details not covered above:

- [using/building-from-source.md](references/using-building-from-source.md)
