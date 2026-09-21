import re,unicodedata
def norm(s):
 s=(s or '').strip().casefold(); s=unicodedata.normalize('NFKD',s); s=''.join(x for x in s if not unicodedata.combining(x)); return re.sub(r'\s+',' ',s)
