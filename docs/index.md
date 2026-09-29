# Data Joinery

<figure markdown="span">
![Image title](images/data-joinery-logo.png){ width="300" }
<figcaption>Schema first data transformations</figcaption>
</figure>

## Overview

Data Joinery is a small framework that allows you to build complex transformation jobs with an emphasis on
testability. It helps you break apart complex transformations into testable units, whilst
allowing you to annotate these transformations with the upstream/downstream schemas. In pyspark
codebases you often see a transformation declared as:

``` python
def get_metrics(fact_table: DataFrame) -> DataFrame:
    ...
```

From this we have no idea what the inputs or outputs of the transformation are. With Data Joinery you
can make it much clearer:

``` python
--8<-- "docs_src/index/intro.py:5:"
```

Using a schema first approach makes it much clearer what this transformation does, for
both you and a coding agent. Data Joinery will also enforce at runtime that the input and output
schemas match the type annotations.

## Installation

Install the package `data-joinery` with your favourite package manager:

``` bash title="Install with pip"
pip install data-joinery
```

``` bash title="Install with uv"
uv add data-joinery
```
