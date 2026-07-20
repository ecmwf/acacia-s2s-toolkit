# ACACIA S2S Toolkit (`acacia-s2s-toolkit`)

> **Disclaimer:** This package is provided for research purposes only. It is **not** intended for use in any operational or production context. It is not an officially supported ECMWF software product.

## Overview

`acacia-s2s-toolkit` is a Python library that supports downloading and post-processing of dynamical sub-seasonal forecast data from the ECMWF Data Store

It builds on [xarray](https://xarray.dev/) for efficient NetCDF-based data handling.

---

## Software Maturity

| Attribute        | Status |
|------------------|--------|
| **Maturity**     | [![Static Badge](https://github.com/ecmwf/codex/raw/refs/heads/main/Project%20Maturity/sandbox_badge.svg)](https://github.com/ecmwf/codex/raw/refs/heads/main/Project%20Maturity#sandbox) |
| **Support level**| Best effort — no guaranteed response time |
| **Operational use** | Not suitable for operational use |


> [!IMPORTANT]
> This software is **Sandbox**, is under active development, and subject to ECMWF's guidelines on [Software Maturity](https://github.com/ecmwf/codex/raw/refs/heads/main/Project%20Maturity). Releases are intended for testing, evaluation, and collaboration rather than production deployment.

---

## Installation

To install the *acacia-s2s-toolkit* on Linux, run the following command:

**python3 -m pip install acacia_s2s_toolkit**

For guidance on installing Python 3 or pip, refer to the official documentation.

---

## Dependencies

The AI-WQ-package requires the following dependencies:

- **numpy** (version 1.23 or higher)
- **xarray** (version 2024.09.0 or higher)
- **dask** (version 2024.9.0)
- **pandas** (version 2.2.3 or higher)
- **scipy** (version 1.14.1 or higher)
- **netCDF4** (version 1.7.2 or higher)
- **requests** (versions 2.32.2 or higher)
- **matplotlib** (versions 3.8 or higher)
- **cartopy** (versions 0.22 or higher)

If these dependencies conflict with your current working environment, consider installing the package in a new virtual environment.

Additionally, to enable automatic download of the appropriate lookup table, you will also need to install the ECMWF sites-toolkit package:

**python3 -m pip install sites-toolkit -i https://get.ecmwf.int/repository/pypi-all/simple**

---

## Upgrading the Package

To upgrade to the latest version, run:

**python3 -m pip install --upgrade acacia_s2s_toolkit**

This project is being actively developed. New updates may be released periodically with detailed annoucements given on the ECMWF-hosted forum.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for the full text.

In applying this licence, ECMWF does not waive the privileges and immunities granted to it by virtue of its status as an intergovernmental organisation, nor does it submit to any jurisdiction.

---

## Support

This package is **not officially supported** by ECMWF. 

For general ECMWF-related enquiries, please use the [ECMWF Service Desk](https://support.ecmwf.int/).

---

## Documentation

Full documentation is available on ReadTheDocs:

**https://acacia-s2s-toolkit.readthedocs.io/en/latest/**
