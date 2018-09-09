import os
import json
import zipfile
import tempfile

import numpy as np
import pandas as pd


class Cell(object):
    """Defines a cell in a table with coordinates relative to a
    left-bottom origin. (pdf coordinate space)

    Parameters
    ----------
    x1 : float
        x-coordinate of left-bottom point.
    y1 : float
        y-coordinate of left-bottom point.
    x2 : float
        x-coordinate of right-top point.
    y2 : float
        y-coordinate of right-top point.

    Attributes
    ----------
    lb : tuple
        Tuple representing left-bottom coordinates.
    lt : tuple
        Tuple representing left-top coordinates.
    rb : tuple
        Tuple representing right-bottom coordinates.
    rt : tuple
        Tuple representing right-top coordinates.
    left : bool
        Whether or not cell is bounded on the left.
    right : bool
        Whether or not cell is bounded on the right.
    top : bool
        Whether or not cell is bounded on the top.
    bottom : bool
        Whether or not cell is bounded on the bottom.
    hspan : bool
        Whether or not cell spans horizontally.
    vspan : bool
        Whether or not cell spans vertically.
    text : string
        Text assigned to cell.
    bound

    """

    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.lb = (x1, y1)
        self.lt = (x1, y2)
        self.rb = (x2, y1)
        self.rt = (x2, y2)
        self.left = False
        self.right = False
        self.top = False
        self.bottom = False
        self.hspan = False
        self.vspan = False
        self._text = ''

    def __repr__(self):
        return '<Cell x1={} y1={} x2={} y2={}>'.format(
            self.x1, self.y1, self.x2, self.y2)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, t):
        self._text = ''.join([self._text, t])

    @property
    def bound(self):
        """The number of sides on which the cell is bounded.
        """
        return self.top + self.bottom + self.left + self.right


class Table(object):
    """Defines a table with coordinates relative to a left-bottom
    origin. (pdf coordinate space)

    Parameters
    ----------
    cols : list
        List of tuples representing column x-coordinates in increasing
        order.
    rows : list
        List of tuples representing row y-coordinates in decreasing
        order.

    Attributes
    ----------
    df : object
        pandas.DataFrame
    shape : tuple
        Shape of the table.
    accuracy : float
        Accuracy with which text was assigned to the cell.
    whitespace : float
        Percentage of whitespace in the table.
    order : int
        Table number on pdf page.
    page : int
        Pdf page number.
    data
    parsing_report

    """
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.cells = [[Cell(c[0], r[1], c[1], r[0])
                       for c in cols] for r in rows]
        self.df = None
        self.shape = (0, 0)
        self.accuracy = 0
        self.whitespace = 0
        self.order = None
        self.page = None

    def __repr__(self):
        return '<{} shape={}>'.format(self.__class__.__name__, self.shape)

    @property
    def data(self):
        """Returns two-dimensional list of strings in table.
        """
        d = []
        for row in self.cells:
            d.append([cell.text.strip() for cell in row])
        return d

    @property
    def parsing_report(self):
        """Returns a parsing report with accuracy, %whitespace,
        table number on page and page number.
        """
        # pretty?
        report = {
            'accuracy': self.accuracy,
            'whitespace': self.whitespace,
            'order': self.order,
            'page': self.page
        }
        return report

    def set_all_edges(self):
        """Sets all table edges to True.
        """
        for row in self.cells:
            for cell in row:
                cell.left = cell.right = cell.top = cell.bottom = True
        return self

    def set_edges(self, vertical, horizontal, joint_close_tol=2):
        """Sets a cell's edges to True depending on whether the cell's
        coordinates overlap with the line's coordinates within a
        tolerance.

        Parameters
        ----------
        vertical : list
            List of detected vertical lines.
        horizontal : list
            List of detected horizontal lines.

        """
        for v in vertical:
            # find closest x coord
            # iterate over y coords and find closest start and end points
            i = [i for i, t in enumerate(self.cols)
                 if np.isclose(v[0], t[0], atol=joint_close_tol)]
            j = [j for j, t in enumerate(self.rows)
                 if np.isclose(v[3], t[0], atol=joint_close_tol)]
            k = [k for k, t in enumerate(self.rows)
                 if np.isclose(v[1], t[0], atol=joint_close_tol)]
            if not j:
                continue
            J = j[0]
            if i == [0]:  # only left edge
                L = i[0]
                if k:
                    K = k[0]
                    while J < K:
                        self.cells[J][L].left = True
                        J += 1
                else:
                    K = len(self.rows)
                    while J < K:
                        self.cells[J][L].left = True
                        J += 1
            elif i == []:  # only right edge
                L = len(self.cols) - 1
                if k:
                    K = k[0]
                    while J < K:
                        self.cells[J][L].right = True
                        J += 1
                else:
                    K = len(self.rows)
                    while J < K:
                        self.cells[J][L].right = True
                        J += 1
            else:  # both left and right edges
                L = i[0]
                if k:
                    K = k[0]
                    while J < K:
                        self.cells[J][L].left = True
                        self.cells[J][L - 1].right = True
                        J += 1
                else:
                    K = len(self.rows)
                    while J < K:
                        self.cells[J][L].left = True
                        self.cells[J][L - 1].right = True
                        J += 1

        for h in horizontal:
            # find closest y coord
            # iterate over x coords and find closest start and end points
            i = [i for i, t in enumerate(self.rows)
                 if np.isclose(h[1], t[0], atol=joint_close_tol)]
            j = [j for j, t in enumerate(self.cols)
                 if np.isclose(h[0], t[0], atol=joint_close_tol)]
            k = [k for k, t in enumerate(self.cols)
                 if np.isclose(h[2], t[0], atol=joint_close_tol)]
            if not j:
                continue
            J = j[0]
            if i == [0]:  # only top edge
                L = i[0]
                if k:
                    K = k[0]
                    while J < K:
                        self.cells[L][J].top = True
                        J += 1
                else:
                    K = len(self.cols)
                    while J < K:
                        self.cells[L][J].top = True
                        J += 1
            elif i == []:  # only bottom edge
                I = len(self.rows) - 1
                if k:
                    K = k[0]
                    while J < K:
                        self.cells[L][J].bottom = True
                        J += 1
                else:
                    K = len(self.cols)
                    while J < K:
                        self.cells[L][J].bottom = True
                        J += 1
            else:  # both top and bottom edges
                L = i[0]
                if k:
                    K = k[0]
                    while J < K:
                        self.cells[L][J].top = True
                        self.cells[L - 1][J].bottom = True
                        J += 1
                else:
                    K = len(self.cols)
                    while J < K:
                        self.cells[L][J].top = True
                        self.cells[L - 1][J].bottom = True
                        J += 1

        return self

    def set_border(self):
        """Sets table border edges to True.
        """
        for r in range(len(self.rows)):
            self.cells[r][0].left = True
            self.cells[r][len(self.cols) - 1].right = True
        for c in range(len(self.cols)):
            self.cells[0][c].top = True
            self.cells[len(self.rows) - 1][c].bottom = True
        return self

    def set_span(self):
        """Sets a cell's hspan or vspan attribute to True depending
        on whether the cell spans horizontally or vertically.
        """
        for row in self.cells:
            for cell in row:
                left = cell.left
                right = cell.right
                top = cell.top
                bottom = cell.bottom
                if cell.bound == 4:
                    continue
                elif cell.bound == 3:
                    if not left and (right and top and bottom):
                        cell.hspan = True
                    elif not right and (left and top and bottom):
                        cell.hspan = True
                    elif not top and (left and right and bottom):
                        cell.vspan = True
                    elif not bottom and (left and right and top):
                        cell.vspan = True
                elif cell.bound == 2:
                    if left and right and (not top and not bottom):
                        cell.vspan = True
                    elif top and bottom and (not left and not right):
                        cell.hspan = True
        return self

    def to_csv(self, path, **kwargs):
        """Write Table to a comma-separated values (csv) file.
        """
        kw = {
            'encoding': 'utf-8',
            'index': False,
            'quoting': 1
        }
        kw.update(kwargs)
        self.df.to_csv(path, **kw)

    def to_json(self, path, **kwargs):
        """Write Table to a JSON file.
        """
        kw = {
            'orient': 'records'
        }
        kw.update(kwargs)
        json_string = self.df.to_json(**kw)
        with open(path, 'w') as f:
            f.write(json_string)

    def to_excel(self, path, **kwargs):
        """Write Table to an Excel file.
        """
        kw = {
            'sheet_name': 'page-{}-table-{}'.format(self.page, self.order),
            'encoding': 'utf-8'
        }
        kw.update(kwargs)
        writer = pd.ExcelWriter(path)
        self.df.to_excel(writer, **kw)
        writer.save()

    def to_html(self, path, **kwargs):
        """Write Table to an HTML file.
        """
        html_string = self.df.to_html(**kwargs)
        with open(path, 'w') as f:
            f.write(html_string)


class TableList(object):
    """Defines a list of camelot.core.Table objects. Each table can
    be accessed using its index.

    Attributes
    ----------
    n : int
        Number of tables in the list.

    """
    def __init__(self, tables):
        self._tables = tables

    def __repr__(self):
        return '<{} tables={}>'.format(
            self.__class__.__name__, len(self._tables))

    def __len__(self):
        return len(self._tables)

    def __getitem__(self, idx):
        return self._tables[idx]

    @staticmethod
    def _format_func(table, f):
        return getattr(table, 'to_{}'.format(f))

    @property
    def n(self):
        return len(self._tables)

    def _write_file(self, f=None, **kwargs):
        dirname = kwargs.get('dirname')
        root = kwargs.get('root')
        ext = kwargs.get('ext')
        for table in self._tables:
            filename = os.path.join('{}-page-{}-table-{}{}'.format(
                                    root, table.page, table.order, ext))
            filepath = os.path.join(dirname, filename)
            to_format = self._format_func(table, f)
            to_format(filepath)

    def _compress_dir(self, **kwargs):
        path = kwargs.get('path')
        dirname = kwargs.get('dirname')
        root = kwargs.get('root')
        ext = kwargs.get('ext')
        zipname = os.path.join(os.path.dirname(path), root) + '.zip'
        with zipfile.ZipFile(zipname, 'w', allowZip64=True) as z:
            for table in self._tables:
                filename = os.path.join('{}-page-{}-table-{}{}'.format(
                                        root, table.page, table.order, ext))
                filepath = os.path.join(dirname, filename)
                z.write(filepath, os.path.basename(filepath))

    def export(self, path, f='csv', compress=False):
        """Exports the list of tables to specified file format.

        Parameters
        ----------
        path : str
            Filepath
        f : str
            File format. Can be csv, json, excel and html.
        compress : bool
            Whether or not to add files to a ZIP archive.

        """
        dirname = os.path.dirname(path)
        basename = os.path.basename(path)
        root, ext = os.path.splitext(basename)
        if compress:
            dirname = tempfile.mkdtemp()

        kwargs = {
            'path': path,
            'dirname': dirname,
            'root': root,
            'ext': ext
        }

        if f in ['csv', 'json', 'html']:
            self._write_file(f=f, **kwargs)
            if compress:
                self._compress_dir(**kwargs)
        elif f == 'excel':
            filepath = os.path.join(dirname, basename)
            writer = pd.ExcelWriter(filepath)
            for table in self._tables:
                sheet_name = 'page-{}-table-{}'.format(table.page, table.order)
                table.df.to_excel(writer, sheet_name=sheet_name, encoding='utf-8')
            writer.save()
            if compress:
                zipname = os.path.join(os.path.dirname(path), root) + '.zip'
                with zipfile.ZipFile(zipname, 'w', allowZip64=True) as z:
                    z.write(filepath, os.path.basename(filepath))


class Geometry(object):
    def __init__(self):
        self.text = []
        self.images = ()
        self.segments = ()
        self.tables = []

    def __repr__(self):
        return '<{} text={} images={} segments={} tables={}>'.format(
            self.__class__.__name__,
            len(self.text),
            len(self.images),
            len(self.segments),
            len(self.tables))


class GeometryList(object):
    def __init__(self, geometry):
        self.text = [g.text for g in geometry]
        self.images = [g.images for g in geometry]
        self.segments = [g.segments for g in geometry]
        self.tables = [g.tables for g in geometry]

    def __repr__(self):
        return '<{} text={} images={} segments={} tables={}>'.format(
            self.__class__.__name__,
            len(self.text),
            len(self.images),
            len(self.segments),
            len(self.tables))