<!-- docs:start -->
# MarketFlows

## PRE-RELEASE

[![CI](https://github.com/elliottbache/marketflows/actions/workflows/ci.yaml/badge.svg)](https://github.com/elliottbache/marketflows/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/github/elliottbache/marketflows/graph/badge.svg?token=kNwbaexX4N)](https://codecov.io/github/elliottbache/marketflows) 
[![Docs](https://img.shields.io/badge/docs-Read%20the%20Docs-brightgreen)](https://marketflows.readthedocs.io/en/latest/?badge=latest)
[![Release](https://img.shields.io/github/v/release/elliottbache/marketflows)](https://github.com/elliottbache/marketflows/releases)
[![License: GPL-3.0](https://img.shields.io/badge/license-%20%20GNU%20GPLv3%20-green?style=plastic)](https://github.com/elliottbache/marketflows/blob/main/LICENSE)

Track capital flows and narrative rotation across markets.

## How it works
This program makes multiple queries when run and may be slow due to rate limits.

## Store locally or query once?
Free plan has 30 calls per minute limit, and we typically would need to make around 150 calls 
for narratives, 10 calls for individual assets, and 430 calls for small-large cap ranges.
<!-- docs:end -->