# 📋 AliveOS Repository TODO & Roadmap

This document tracks planned packages, kernel module builds, and repository infrastructure tasks.

---

## 🎯 Kernel Modules & Hardware Drivers

### 1. NVIDIA 580.xx Prebuilt Kernel Module (`nvidia-580xx-cachyos-lts-v2`)
- [ ] **Create pre-built binary module package for `linux-cachyos-lts-v2`**:
  - **Upstream / AUR Base**: `nvidia-580xx-utils` (AUR: `nvidia-580xx-dkms`, `nvidia-580xx-utils`, `opencl-nvidia-580xx`).
  - **Package Name**: `packages/nvidia-580xx-cachyos-lts-v2`
  - **Module Targets**:
    - `nvidia.ko`
    - `nvidia-modeset.ko`
    - `nvidia-drm.ko`
    - `nvidia-uvm.ko`
    - `nvidia-peermem.ko`
  - **Installation Path**: `/usr/lib/modules/${_kernver}/extramodules/` (compressed with `zstd -19`).
  - **Dependencies**:
    - `depends=('linux-cachyos-lts-v2' "nvidia-580xx-utils=${pkgver}")`
    - `makedepends=('linux-cachyos-lts-v2-headers')`
    - `provides=('NVIDIA-MODULE')`
    - `conflicts=('nvidia-580xx-dkms')`
  - **Build Strategy**:
    - Extract module sources from the NVIDIA `.run` installer or leverage `fakeroot dkms build --dkmstree "${srcdir}" -m nvidia/${pkgver} -k ${_kernver}`.
    - Include upstream patches:
      - `0001-Enable-atomic-kernel-modesetting-by-default.patch` (atomic KMS modesetting).
      - `0002-Fix-hardware-cursor-crash.patch` (Wayland hardware cursor stability fix).
  - **Repository Integration**:
    - Add to `scripts/build-packages.sh`:
      - `aur|nvidia-580xx-utils|` (or local if customized)
      - `local|nvidia-580xx-cachyos-lts-v2|`
      - `aur|lib32-nvidia-580xx-utils|`
      - `aur|nvidia-580xx-settings|`
    - Update `README.md` package list.

---

## 📦 General Packages Backlog

- [ ] **Verify CI/CD GitHub Actions build pipeline with newly added packages**:
  - Ensure `muse-code` and prebuilt modules compile cleanly in the weekly runner container.
