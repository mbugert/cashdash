# CashDash

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Interactive visualization of GnuCash data based on plotly Dash.
Currently in pre-alpha state, but already usable.

## Features
* reads gnucash XML files
* **automatically creates a Sankey graph from transactions**, with lots of configuration options 
* visualizes assets and expenses over time

## Installation
You need Python 3.7+. Clone the repository, then run:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install git+https://github.com/fovea1959/gnucashxml
```

## Usage
Run `python app.py PATH_TO_GNUCASH_XML_FILE` and navigate to `http://localhost:8080`.

Try the included sample! `python app.py cashdash/resources/sample_books/gnucash_xml.gnucash`

## Optional dependencies
By default, the [cvxpy library](https://cvxpy.org/) is used to compute Sankey links from complex split transactions.
[minizinc](https://minizinc.org/) can be used as an optional replacement which is slower but should be more precise. In this case you need python **3.8+**. Install minizinc via
```
snap install minizinc --classic
```
or check alternative installation options [on their website](https://www.minizinc.org/doc-2.3.2/en/installation.html).

To use it, run the app via `--backend minizinc`.