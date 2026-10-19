"""Demo sites for prospects: a food producer and a clothing workshop.

USE A DEDICATED DEMO SITE (ERPNext + dz_core only), NEVER A CLIENT SITE.

    bench --site food-demo.localhost execute dz_core.demo.loader.load --kwargs "{'profile': 'food'}"

How it is built (docs/DEMO.md):
- data.py-style modules hold the business (food.py, clothing.py): who buys,
  who sells, what is made from what, and the story of the last weeks;
- the masters go in through the client import workbook (workbook.py), exactly
  as a real client's data would;
- the history is replayed day by day through real ERPNext documents
  (engine.py): purchase orders, receipts, work orders, deliveries, invoices,
  payments, returns, stock counts.
"""
