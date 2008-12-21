"""
Simple text utilities.
- SimpleTable
- WordFreq

Note that this module depends only on the Python standard library.
You can "install" it just by dropping it into your working directory.

:contact: alan dot isaac at gmail dot com
:requires: Python 2.5.1+
:todo: add support for recarray to SimpleTable
:todo: allow user access to 2d matrix of strings (the table or table data)
:date: 2008-12-21
"""
from __future__ import division, with_statement
import sys, string
from itertools import izip, cycle
from collections import defaultdict

class SimpleTable:
	"""Produce a simple ASCII, CSV, or LaTeX table from a
	rectangular array of data, not necessarily numerical. 
	Supports at most one header row,
	which must be the length of data[0] (or +1 if stubs).
	Supports at most one stubs column, which must be the length of data.
	See methods `default_txt_fmt`, `default_csv_fmt`,
	and `default_ltx_fmt` for formatting options.

	Sample uses::

		mydata = [[11,12],[21,22]]
		myheaders = "Column 1", "Column 2"
		mystubs = "Row 1", "Row 2"
		tbl = text.SimpleTable(mydata, myheaders, mystubs, title="Title")
		print( tbl.as_text() )
		print( tbl.as_latex_tabular() )
		#write table as CSV file
		#  note column specific formatting
		tbl = text.SimpleTable(mydata, myheaders, mystubs,
			fmt={'data_fmt':["%3.2f","%d"]})
		with open('c:/temp/temp.csv','w') as fh:
			fh.write( tbl.as_csv() )
	"""
	def __init__(self, data, headers=(), stubs=(), title='', fmt=None,
		csv_fmt=None, txt_fmt=None, ltx_fmt=None):
		"""
		:Parameters:
			data : list of lists or 2d array
				R rows by K columns of table data
			headers: tuple
				sequence of K strings, one per header
			stubs: tuple
				sequence of R strings, one per stub
			fmt : dict
				formatting options
			txt_fmt : dict
				text formatting options
			ltx_fmt : dict
				latex formatting options
			csv_fmt : dict
				csv formatting options
		"""
		self.data = data
		self.headers = headers
		self.stubs = tuple(str(stub) for stub in stubs)
		self.title = title
		#start with default formatting
		self.txt_fmt = self.default_txt_fmt()
		self.ltx_fmt = self.default_ltx_fmt()
		self.csv_fmt = self.default_csv_fmt()
		#substitute any user specified formatting
		if fmt:
			self.csv_fmt.update(fmt)
			self.txt_fmt.update(fmt)
			self.ltx_fmt.update(fmt)
		self.csv_fmt.update(csv_fmt or dict())
		self.txt_fmt.update(txt_fmt or dict())
		self.ltx_fmt.update(ltx_fmt or dict())
	def __str__(self):
		return self.as_text()
	def _format_rows(self, tablestrings, fmt_dict):
		"""Return: list of strings,
		the formatted table data with headers and stubs.
		Note that `tablestrings` is a rectangular iterable of strings.
		"""
		fmt = fmt_dict['fmt']
		colwidths = self.get_colwidths(tablestrings, fmt_dict)
		cols_aligns = self.get_cols_aligns(fmt_dict)
		colsep = fmt_dict['colsep']
		pre = fmt_dict.get('pre','')
		post = fmt_dict.get('post','')
		nrows = len(tablestrings)
		rows = []
		for row in tablestrings:
			cols = []
			for k in range(nrows):
				d = row[k]
				align = cols_aligns[k]
				width = colwidths[k]
				d = self.pad(d, width, align)
				cols.append(d)
			rows.append( pre + colsep.join(cols) + post )
		return rows
	def pad(self, s, width, align):
		"""Return string padded with spaces,
		based on alignment parameter."""
		if align == 'l':
			s = s.ljust(width)
		elif align == 'r':
			s = s.rjust(width)
		else:
			s = s.center(width)
		return s
	def _format_data(self, fmt_dict):
		"""Return list of lists,
		the formatted data (without headers or stubs).
		Note: does *not* change `self.data`."""
		data_fmt = fmt_dict.get('data_fmt','%s')
		if isinstance(data_fmt, str):
			result = [[(data_fmt%drk) for drk in dr] for dr in self.data]
		else:
			fmt = cycle( data_fmt )
			result = [[(fmt.next()%drk) for drk in dr] for dr in self.data]
		return result
	def format_headers(self, fmt_dict, headers=None):
		"""Return list, the formatted headers."""
		header_fmt = fmt_dict.get('header_fmt','%s')
		headers2fmt = headers or self.headers
		return [header_fmt%header for header in headers2fmt]
	def format_stubs(self, fmt_dict, stubs=None):
		"""Return list, the formatted stubs."""
		stub_fmt = fmt_dict.get('stub_fmt','%s')
		stubs2fmt = stubs or self.stubs
		return [stub_fmt%stub for stub in stubs2fmt]
	def merge_table_parts(self, data, headers, stubs): #avoids copy; too implicit?
		"""Return None. Insert stubs and headers into `data`."""
		for i in range(len(stubs)):
			data[i].insert(0,stubs[i])
		if headers:
			data.insert(0,headers)
		if stubs and headers:
			data[0].insert(0,'')
	def as_csv(self, **fmt):
		"""Return string, the table in CSV format.
		Currently only supports comma separator."""
		#fetch the format, which may just be default_csv_format
		fmt_dict = self.csv_fmt.copy()
		#update format using `fmt`
		fmt_dict.update(fmt)
		return self.as_text(**fmt_dict)
	def as_text(self, **fmt):  #allow changing fmt here?
		"""Return string, the table as text."""
		fmt_dict = self.txt_fmt.copy()
		fmt_dict.update(fmt)
		#data_fmt="%s", header_fmt="%s", stub_fmt="%s", colsep=" ", data_aligns='', colwidths=(), header_dec=''):
		#format the 3 table parts (data, headers, stubs) and merge in list of lists
		# first get data as 2d list of strings (no headers or stubs)
		txt_data = self._format_data(fmt_dict)
		txt_headers = self.format_headers(fmt_dict)
		txt_stubs = self.format_stubs(fmt_dict)
		self.merge_table_parts(txt_data, txt_headers, txt_stubs)
		#do a column width check before formatting
		rows = self._format_rows(txt_data, fmt_dict)
		headerlen = len(rows[0])
		begin = ''
		if self.title:
			begin += self.pad(self.title, headerlen, fmt_dict['title_align'])
		#decoration above the table, if desired
		table_dec_above = fmt_dict['table_dec_above']
		if table_dec_above:
			begin += "\n" + table_dec_above*headerlen
		if txt_headers:
			hdec = fmt_dict['header_dec_below']
			if hdec:
				rows[0] = rows[0] + "\n" + hdec*headerlen
		end = ''
		below = fmt_dict['table_dec_below']
		if below:
			end = below*headerlen + "\n" + end
		return begin + "\n" + '\n'.join(rows) + "\n" + end
	def get_colwidths(self, tablestrings, fmt_dict):
		"""Return list of int, the column widths.
		Ensure comformable colwidths in `fmt_dict`.
		Other, compute as the max width for each column of `tablestrings`.
		Note that `tablestrings` is a rectangular iterable of strings.
		"""
		ncols = len(tablestrings[0])
		request_widths = fmt_dict.get('colwidths')
		if request_widths is None:
			result = [0] * ncols
		else:
			min_widths = [max(len(d) for d in c) for c in izip(*tablestrings)]
			if isinstance(request_widths, int):
				request_widths = cycle([request_widths])
			elif len(request_widths) != ncols:
				request_widths = min_widths
			result = [max(m,r) for m,r in izip(min_widths, request_widths)]
		return result
	def get_cols_aligns(self, fmt_dict):
		"""Return string, sequence of column alignments.
		Ensure comformable data_aligns in `fmt_dict`."""
		ncols = len(self.data[0])
		cols_aligns = fmt_dict.get('cols_aligns')
		if cols_aligns is None or len(cols_aligns) != ncols:
			if self.stubs:
				ncols -= 1
				stubs_align = fmt_dict.get('stubs_align')
				if stubs_align is None:
					stubs_align = 'l'
			else:
				stubs_align = ''
			data_aligns = fmt_dict.get('data_aligns')
			if data_aligns is None:
				data_aligns = 'c'*(ncols)
			cols_aligns = stubs_align + data_aligns
		return cols_aligns
	def as_latex_tabular(self, **fmt):
		'''Return string, the table as a LaTeX tabular environment.
		Note: will equire the booktabs package.'''
		fmt_dict = self.ltx_fmt.copy()
		fmt_dict.update(fmt)
		ltx_data = self._format_data(fmt_dict)
		if fmt_dict['strip_backslash']:
			ltx_headers = [header.replace("\\","$\\backslash$") for header in self.headers]
			ltx_stubs = [stub.replace("\\",r'$\backslash$') for stub in self.stubs]
		ltx_headers = self.format_headers(fmt_dict, ltx_headers)
		ltx_stubs = self.format_stubs(fmt_dict, ltx_stubs)
		#check column alignments *before* data merge
		self.merge_table_parts(ltx_data, ltx_headers, ltx_stubs)
		#this just formats output; add real colwidths?
		fmt_dict['post'] = r'  \\'
		#rows = self._format_rows(ltx_data, data_aligns, colsep, post=)
		rows = self._format_rows(ltx_data, fmt_dict)
		data_aligns = fmt_dict['data_aligns']
		begin = r'\begin{tabular}{%s}'%data_aligns
		above = fmt_dict['table_dec_above']
		if above:
			begin += "\n" + above + "\n"
		if ltx_headers:
			hdec = fmt_dict['header_dec_below']
			if hdec:
				rows[0] = rows[0] + "\n" + hdec
		end = r'\end{tabular}'
		below = fmt_dict['table_dec_below']
		if below:
			end = below + "\n" + end
		return begin + '\n'.join(rows) + "\n" + end
	#########  begin: default formats  ##############
	def default_csv_fmt(self):
		dcf = dict(
			data_fmt = '%s',
			colwidths = None,
			colsep = ',',
			table_dec_above = '',
			table_dec_below = '',
			header_dec_below = '',
			title_align = '',
			header_fmt = '"%s"',
			stub_fmt = '"%s"',
			data_aligns = "l"*(len(self.data[0])),
			stubs_align = "l",
			fmt = 'csv',
			)
		return dcf
	def default_txt_fmt(self):
		dtf = dict(
			data_fmt = "%s",
			colwidths = 0,
			colsep=' ',
			table_dec_above='=',
			table_dec_below='-',
			header_dec_below='-',
			title_align='c',
			data_aligns = "c"*(len(self.data[0])),
			stub_fmt = '%s',
			stubs_align = "l",
			fmt = 'txt',
			)
		return dtf
	def default_ltx_fmt(self):
		dlf = dict(
			data_fmt = "%s",
			colsep=' & ',
			table_dec_above = r'\toprule',
			table_dec_below = r'\bottomrule',
			header_dec_below = r'\midrule',
			strip_backslash = True,
			header_fmt = "\\textbf{%s}",
			stub_fmt = "\\textbf{%s}",
			data_aligns = "c"*(len(self.data[0])),
			stubs_align = "l",
			fmt = 'ltx',
			)
		return dlf
	#########  end: default formats  ##############


class WordFreq:
	"""Summarize text file word counts.
	"""
	def __init__(self, filename, **kw):
		self.filename = filename
		self.params = kw
		self.result = self.describe()
	def describe(self):
		"""
		might want, e.g.,
		START_AFTER = ".. begin wordcount",
		"""
		params = dict(
		start_after = '',
		wordsize_min = 3,
		freq_min = 2
		)
		params.update(self.params)
		self.params = params
		start_after = params['start_after']
		wordsize_min = params['wordsize_min']
		chars2strip = string.punctuation
		ct_words = 0
		ct_longwords = 0
		word_hash = defaultdict(int)
		with open(self.filename,'r') as fh:
			for line in fh:
				while start_after:
					if line.startswith(START_AFTER):
						start_after = False
					continue
				line.strip()
				for word in line.split():
					word = word.strip(chars2strip)
					if word:
						ct_words += 1
					if len(word) >= wordsize_min:
						ct_longwords += 1
						word_hash[word] += 1
		result = dict(word_hash=word_hash,
		ct_words=ct_words,
		ct_longwords=ct_longwords
		)
		return result
	def summarize(self):
		freq_min = self.params['freq_min']
		result = self.result
		fmt = "%24s %6d"
		print "Results for 'longer' words (length >= %(wordsize_min)d)."%self.params
		print """
		=================================================
		=============== WORD COUNT ======================
		=================================================
		Total number of words: %(ct_words)d
		Total number of 'longer' words : %(ct_longwords)d
		"""%result

		print """
		=================================================
		=============== ALPHA ORDER =====================
		=================================================
		"""
		for k,v in sorted( result['word_hash'].iteritems() ):
			if v >= freq_min:
				print fmt%(k,v)
		print """
		=================================================
		============ OCCURRENCE ORDER ===================
		=================================================
		"""
		for k,v in sorted( result['word_hash'].iteritems(), key = lambda x: (-x[1], x[0]) ):
			if v >= freq_min:
				print fmt%(k,v)
