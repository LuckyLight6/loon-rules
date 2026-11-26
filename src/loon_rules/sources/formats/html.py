"""Shared HTML table parsing, independent of Loon rule syntax."""
from collections import defaultdict
from html.parser import HTMLParser

HIDDEN_HTML=frozenset({'script','style','template','noscript'})

class HostTables(HTMLParser):
    """Consume host/role cells without preserving editorial text."""
    def __init__(self,*,ignore_controls=False):
        super().__init__()
        self.hidden_tags=HIDDEN_HTML|({'button'} if ignore_controls else set())
        self.tables=defaultdict(list)
        self._table_stack=[]
        self.section = ''
        self.rows = defaultdict(list)
        self.row = self.cell = None
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.hidden_tags:self.hidden+=1
        if self.hidden:return
        if tag=='br' and self.cell is not None:
            self.cell.append(' ')
        if tag=='table':
            if self._table_stack:self._table_stack[-1]['nested']=True
            table={'rows':[],'nested':False}
            self.tables[self.section].append(table)
            self._table_stack.append(table)
        if tag=='h2':
            self.section=dict(attrs).get('id') or ''
        elif tag=='tr':
            self.row=[]
        elif self.row is not None and tag in ('td','th'):
            self.cell=[]

    def handle_data(self, value):
        if self.cell is not None and not self.hidden:
            self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in self.hidden_tags:self.hidden=max(0,self.hidden-1);return
        if self.hidden:return
        if tag=='table':
            if self._table_stack:self._table_stack.pop()
            return
        if tag in ('td','th') and self.cell is not None:
            self.row.append(''.join(self.cell).strip())
            self.cell=None
        if tag=='tr' and self.row is not None:
            if self.row:
                self.record(self.row)
            self.row=None


    def record(self,row):
        self.rows[self.section].append(row)
        if self._table_stack:self._table_stack[-1]['rows'].append(row)


class AppleTables(HostTables):
    def record(self,row):
        if len(row)>=5:
            self.rows[self.section].append((row[0],row[4]))
