#!python3

## Import General Tools
from pathlib import Path
from datetime import datetime, timedelta
import os


def main():
    now = datetime.utcnow()
    oneday = timedelta(days=1)
    target_date = now.strftime('%Y%m%dUT') if now.hour > 3\
                  else (now-oneday).strftime('%Y%m%dUT')
    p = Path(f'~/V5Data/Images/{target_date}').expanduser()
    print(p)

if __name__ == '__main__':
    main()
