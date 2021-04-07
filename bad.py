import sys
from humanize import intcomma
from datetime import datetime
import mwclient
from itertools import islice

site = mwclient.Site('en.wikipedia.org')

CATEGORY = 'Living people'

t0 = datetime.now()
pages = 0
found = 0

for page in site.categories[CATEGORY]:
    if not isinstance(page, mwclient.listing.Category):
        pages += 1
        if pages % 10000 == 0:
            print(f'Examined {intcomma(pages)} pages, found {intcomma(found)} in {datetime.now() - t0}', file=sys.stderr)
            if '</ref>' not in page.text():
                print(page)
                found += 1
