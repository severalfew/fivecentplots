import pandas as pd
import numpy as np
import fivecentplots.utilities as utl
import scipy.stats as ss

try:
    from natsort import natsorted
except:
    natsorted = sorted

import pdb
st = pdb.set_trace

REQUIRED_VALS = {'plot_xy': ['x', 'y'],
                 'plot_box': ['y'],
                 'plot_hist': ['x'],
                 'plot_contour': ['x', 'y', 'z'],
                 'plot_heatmap': [],
                }
OPTIONAL_VALS = {'plot_xy': [],
                 'plot_box': [],
                 'plot_hist': [],
                 'plot_contour': [],
                 'plot_heatmap': ['x', 'y', 'z'],
                }


class AxisError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class DataError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class GroupingError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class Data:
    def __init__(self, plot_func='xy', **kwargs):

        #from fivecentplots.fcp import utl.kwget, reload_defaults

        # Reload default file
        self.fcpp, dummy, dummy2 = utl.reload_defaults()

        # Set the plot type
        self.plot_func = plot_func

        # Default axis attributes
        self.auto_scale = utl.kwget(kwargs, self.fcpp, 'auto_scale', True)
        if self.plot_func in ['plot_heatmap', 'plot_hist']:
            self.auto_scale = False
        self.ax_scale = kwargs.get('ax_scale', None)
        self.ax_limit_pad(**kwargs)
        self.conf_int = kwargs.get('conf_int', False)
        self.fit = kwargs.get('fit', False)
        self.fit_range_x = utl.kwget(kwargs, self.fcpp, 'fit_range_x', None)
        self.fit_range_y = utl.kwget(kwargs, self.fcpp, 'fit_range_y', None)
        self.legend = None
        self.legend_vals = None
        self.ranges = None
        self.share_col = utl.kwget(kwargs, self.fcpp, 'share_col', False)
        self.share_row = utl.kwget(kwargs, self.fcpp, 'share_row', False)
        self.share_x = utl.kwget(kwargs, self.fcpp, 'share_x', True)
        self.share_x2 = utl.kwget(kwargs, self.fcpp, 'share_x2', True)
        self.share_y = utl.kwget(kwargs, self.fcpp, 'share_y', True)
        self.share_y2 = utl.kwget(kwargs, self.fcpp, 'share_y2', True)
        self.share_z = utl.kwget(kwargs, self.fcpp, 'share_z', True)
        if self.share_row or self.share_col:
            self.share_x = False
            self.share_y = False
        if kwargs.get('wrap', None) is not None:
            self.share_x = True
            self.share_y = True
        if kwargs.get('wrap', None) == 'y' or kwargs.get('wrap', None) == 'x':
            self.share_x = kwargs.get('share_x', True)
            self.share_y = kwargs.get('share_y', True)
        if self.plot_func in ['plot_box']:
            self.share_x = False
        self.twin_x = kwargs.get('twin_x', False)
        self.twin_y = kwargs.get('twin_y', False)
        if self.twin_x == self.twin_y and self.twin_x:
            raise AxisError('cannot simultaneously twin x and y axes')
        self.xtrans = kwargs.get('xtrans', None)
        self.x2trans = kwargs.get('x2trans', None)
        self.ytrans = kwargs.get('ytrans', None)
        self.y2trans = kwargs.get('y2trans', None)
        self.ztrans = kwargs.get('ztrans', None)
        self.xmin = kwargs.get('xmin', None)
        self.x2min = kwargs.get('x2min', None)
        self.xmax = kwargs.get('xmax', None)
        self.x2max = kwargs.get('x2max', None)
        self.ymin = kwargs.get('ymin', None)
        self.y2min = kwargs.get('y2min', None)
        self.ymax = kwargs.get('ymax', None)
        self.y2max = kwargs.get('y2max', None)
        self.zmin = kwargs.get('zmin', None)
        self.zmax = kwargs.get('zmax', None)

        # Define DataFrames
        self.df_all = self.check_df(kwargs.get('df'))
        self.df_fig = None
        self.df_sub = None
        self.changes = pd.DataFrame()  # used with boxplots
        self.indices = pd.DataFrame()  # used with boxplots

        # Get the x, y, and (optional) axis column names and error check
        self.x = utl.validate_list(kwargs.get('x'))
        self.y = utl.validate_list(kwargs.get('y'))
        self.z = utl.validate_list(kwargs.get('z'))
        self.x = self.check_xyz('x')
        self.y = self.check_xyz('y')
        self.z = self.check_xyz('z')
        if self.twin_x:
            if len(self.y) < 2:
                raise AxisError('twin_x requires two y-axis columns')
            self.y2 = [self.y[1]]
        if self.twin_y:
            if len(self.x) < 2:
                raise AxisError('twin_y requires two x-axis columns')
            self.x2 = [self.x[1]]
        if self.plot_func == 'plot_heatmap':
            if not self.x and not self.y and not self.z:
                self.x = ['Column']
                self.y = ['Row']
                self.z = ['Value']
                self.pivot = False
                self.auto_cols = True
            else:
                self.pivot = True
                self.auto_cols = False

        # Ref line
        self.ref_line = kwargs.get('ref_line', None)
        if type(self.ref_line) is pd.Series:
            self.df_all['Ref Line'] = self.ref_line

        # Stats
        self.stat = kwargs.get('stat', None)
        self.stat_val = kwargs.get('stat_val', None)
        if self.stat_val is not None and self.stat_val not in self.df_all.columns:
            raise DataError('stat_val column "%s" not in DataFrame' % self.stat_val)
        self.stat_idx = []
        self.lcl = []
        self.ucl = []

        # Special for hist
        normalize = utl.kwget(kwargs, self.fcpp, 'hist_normalize', kwargs.get('normalize', False))
        kde=utl.kwget(kwargs, self.fcpp, 'hist_kde', kwargs.get('kde', False))
        if normalize or kde:
            self.norm = True
        else:
            self.norm = False
        self.bins = utl.kwget(kwargs, self.fcpp, 'hist_bins', kwargs.get('bins', 20))

        # Apply an optional filter to the data
        self.filter = kwargs.get('filter', None)
        if self.filter:
            self.df_all = self.df_filter(self.filter)
            if len(self.df_all) == 0:
                raise DataError('DataFrame is empty after applying filter')
        # Define rc grouping column names
        self.col = self.check_group_columns('col', kwargs.get('col', None))
        self.col_vals = None
        self.row = self.check_group_columns('row', kwargs.get('row', None))
        self.row_vals = None
        self.wrap = kwargs.get('wrap', None)
        self.wrap_vals = None
        if self.wrap is not None:
            if self.wrap == 'y':
                self.wrap_vals = [f for f in self.y]
            elif self.wrap == 'x':
                self.wrap_vals = [f for f in self.x]
            else:
                self.wrap = self.check_group_columns('wrap', self.wrap)
        self.groups = self.check_group_columns('groups', kwargs.get('groups', None))
        self.check_group_errors()
        self.ncols = kwargs.get('ncol', 0)
        self.ncol = 1
        self.nleg = 0
        self.nrow = 1
        self.nwrap = 0
        self.ngroups = 0

        # Define legend grouping column names (legends are common to a figure,
        #   not an rc subplot)
        if 'legend' in kwargs.keys():
            if kwargs['legend'] is True:
                self.legend = True
            elif kwargs['legend'] is False:
                self.legend = False
            else:
                self.legend = self.check_group_columns('legend',
                                                       kwargs.get('legend', None))
        elif not self.twin_x and self.y is not None and len(self.y) > 1:
            self.legend = True

        # Define figure grouping column names
        if 'fig_groups' in kwargs.keys():
            self.fig = self.check_group_columns('fig',
                                                kwargs.get('fig_groups', None))
        else:
            self.fig = self.check_group_columns('fig', kwargs.get('fig', None))
        self.fig_vals = None

        # Make sure groups, legend, and fig_groups are not the same
        if self.legend and self.groups and self.plot_func != 'plot_box':
            if type(self.legend) is not bool:
                self.check_group_matching('legend', 'groups')
        if self.legend and self.fig:
            self.check_group_matching('legend', 'fig')
        if self.groups and self.fig:
            self.check_group_matching('groups', 'fig')

        # Other kwargs
        for k, v in kwargs.items():
            if not hasattr(self, k):  # k not in ['df', 'plot_func', 'x', 'y', 'z']:
                setattr(self, k, v)

    def ax_limit_pad(self, **kwargs):
        """
        Set padding limits for axis
        """

        if self.plot_func in ['plot_contour', 'plot_heatmap']:
            self.ax_limit_padding = kwargs.get('ax_limit_padding', None)
        elif self.plot_func in ['plot_hist']:
            self.ax_limit_padding = kwargs.get('ax_limit_padding', 0)
            self.ax_limit_padding_y_max = kwargs.get('ax_limit_padding', 0.05)
        else:
            self.ax_limit_padding = utl.kwget(kwargs, self.fcpp, 'ax_limit_padding', 0.05)
        for ax in ['x', 'x2', 'y', 'y2', 'z']:
            if not hasattr(self, 'ax_limit_padding_%s_min' % ax):
                setattr(self, 'ax_limit_padding_%s_min' % ax,
                        utl.kwget(kwargs, self.fcpp,
                                  'ax_limit_padding_%s_min' % ax, self.ax_limit_padding))
            if not hasattr(self, 'ax_limit_padding_%s_max' % ax):
                setattr(self, 'ax_limit_padding_%s_max' % ax,
                        utl.kwget(kwargs, self.fcpp,
                                  'ax_limit_padding_%s_max' % ax, self.ax_limit_padding))

    def check_df(self, df):
        """
        Validate the dataframe
        """

        if df is None:
            raise DataError('Must provide a DataFrame called "df" '
                             'for plotting!')

        if len(df) == 0:
            raise DataError('DataFrame is empty.  Nothing to plot!')

        return df.copy()

    def check_group_columns(self, group_type, col_names):
        """
        Check wrap/row/column grouping variables for errors

        Args:
            group_type (str): type of grouping (row, col, leg, wrap)
            col_name (str): name of the column by which to group

        """

        # Force list type
        values = utl.validate_list(col_names)

        # Check that each value exists in the dataframe
        if values is None:
            return

        for val in values:
            if val not in self.df_all.columns:
                raise GroupingError('Grouping column "%s" is not '
                                    'in the DataFrame!' % val)

        # Check for no groups
        if len(natsorted(list(self.df_all.groupby(values).groups.keys()))) == 0:
            raise GroupingError('The number of unique groups in the data for '
                                'the "%s=[%s]" is 0' %
                                (group_type, ', '.join(col_names)))

        # Check for wrap with twiny
        if group_type == 'wrap' and col_names is not None and self.twin_y:
            raise GroupingError('Wrap plots do not support twinning of the y-axis. '
                                'Please consider a row vs column plot instead.')

        return values

    def check_group_matching(self, group1, group2):
        """
        Check to make sure certain group column values are not the same

        Args:
            group1 (str): attr name of first grouping column
            group2 (str): attr name of second grouping column

        """

        equal = set(getattr(self, group1)) == set(getattr(self, group2))

        if equal:
            raise GroupingError('%s and %s grouping columns cannot be the same!'
                                % (group1, group2))

    def check_group_errors(self):
        """
        Check for common errors related to grouping keywords
        """

        if self.row and len(self.row) > 1 or self.col and len(self.col) > 1:
            error = 'Only one value can be specified for "%s"' % ('row' if self.row else 'col')
            raise GroupingError(error)

        if self.row is not None and self.row == self.col:
            raise GroupingError('Row and column values must be different!')

        if self.wrap and (self.col or self.row):
            error = 'Cannot combine "wrap" grouping with "%s"' % ('col' if self.col else 'row')
            raise GroupingError(error)

        if self.groups is not None and \
                ((self.row and self.row[0] in self.groups) or \
                 (self.col and self.col[0] in self.groups)):
            error = '"%s" value cannot also be specified as a "group" value' % \
                    ('col' if self.col else 'row')
            raise GroupingError(error)

        if self.groups is not None and self.wrap is not None:
            if len(list(set(self.wrap) & set(self.groups))) > 0:
                error = '"%s" value cannot also be specified as a "group" value' % \
                        ('col' if self.col else 'row')
                raise GroupingError(error)

    def check_xyz(self, xyz):
        """
        Validate the name and column data provided for x, y, and/or z
        Args:
            xyz (str): name of variable to check
        TODO:
            add option to recast non-float/datetime column as categorical str
        """

        if xyz not in REQUIRED_VALS[self.plot_func] and \
                xyz not in OPTIONAL_VALS[self.plot_func]:
            return

        if xyz in OPTIONAL_VALS[self.plot_func] and getattr(self, xyz) is None:
            return None

        vals = getattr(self, xyz)

        if vals is None and xyz not in OPTIONAL_VALS[self.plot_func]:
            raise AxisError('Must provide a column name for "%s"' % xyz)

        for val in vals:
            if val not in self.df_all.columns:
                raise DataError('No column named "%s" found in DataFrame' % val)

            # Check case
            if self.plot_func == 'plot_heatmap':
                continue
            try:
                self.df_all[val] = self.df_all[val].astype(float)
                continue
            except:
                pass
            try:
                self.df_all[val] = self.df_all[val].astype('datetime64[ns]')
                continue
            except:
                raise AxisError('Could not convert x-column "%s" to float or '
                                 'datetime.' % val)

        # Check for axis errors
        if self.twin_x and len(self.y) != 2:
            raise AxisError('twin_x error! %s y values were specified but'
                            ' two are required' % len(self.y))
        if self.twin_x and len(self.x) > 1:
            raise AxisError('twin_x error! only one x value can be specified')
        if self.twin_y and len(self.x) != 2:
            raise AxisError('twin_y error! %s x values were specified but'
                            ' two are required' % len(self.x))
        if self.twin_y and len(self.y) > 1:
            raise AxisError('twin_y error! only one y value can be specified')
        # if len(self.y) > 1 and len(self.x) > 1 and len(self.y) != len(self.x):
        #     raise AxisError('too many axes! Number of x and y axes specified '
        #                     'must match OR at least one axis must contain '
        #                     'only one value')

        return vals

    def df_filter(self, filt_orig):
        """  Filter the DataFrame

        Due to limitations in pd.query, column names must not have spaces.  This
        function will temporarily replace spaces in the column names with
        underscores, but the supplied query string must contain column names
        without any spaces

        Args:
            filt_orig (str):  query expression for filtering

        Returns:
            filtered DataFrame
        """

        def special_chars(text, skip=[]):
            """
            Replace special characters in a text string

            Args:
                text (str): input string
                skip (list): characters to skip

            Returns:
                formatted string
            """

            chars = {' ': '_', '.': 'dot', '[': '',']': '', '(': '', ')': '',
                     '-': '_', '^': '', '>': '', '<': '', '/': '_', '@': 'at',
                     '%': 'percent', '*': '_'}
            for sk in skip:
                chars.pop(sk)
            for k, v in chars.items():
                text = text.replace(k, v).lstrip(' ').rstrip(' ')
            return text

        df2 = self.df_all.copy()

        # Parse the filter string
        filt = utl.get_current_values(df2, filt_orig)

        # Remove spaces from
        cols_orig = [f for f in self.df_all.columns]
        cols_new = ['fCp%s' % f for f in cols_orig.copy()]
        cols_new = [special_chars(f) for f in cols_new]

        df2.columns = cols_new

        # Reformat the filter string for compatibility with pd.query
        operators = ['==', '<', '>', '!=']
        ands = [f.lstrip().rstrip() for f in filt.split('&')]
        for ia, aa in enumerate(ands):
            ors = [f.lstrip() for f in aa.split('|')]
            for io, oo in enumerate(ors):
                # Temporarily remove any parentheses
                param_start = False
                param_end = False
                if oo[0] == '(':
                    oo = oo[1:]
                    param_start = True
                if oo[-1] == ')':
                    oo = oo[0:-1]
                    param_end = True
                for op in operators:
                    if op not in oo:
                        continue
                    vals = oo.split(op)
                    vals[0] = vals[0].rstrip()
                    vals[1] = vals[1].lstrip()
                    if vals[1] == vals[0]:
                        vals[1] = 'fCp%s' % special_chars(vals[1])
                    vals[0] = 'fCp%s' % special_chars(vals[0])
                    ors[io] = op.join(vals)
                    if param_start:
                        ors[io] = '(' + ors[io]
                    if param_end:
                        ors[io] = ors[io] + ')'
            if len(ors) > 1:
                ands[ia] = '|'.join(ors)
            else:
                ands[ia] = ors[0]
        if len(ands) > 1:
            filt = '&'.join(ands)
        else:
            filt = ands[0]

        # Apply the filter
        try:
            df2 = df2.query(filt)
            df2.columns = cols_orig

            return df2

        except:
            print('Could not filter data!\n   Original filter string: %s\n   '
                  'Modified filter string: %s' % (filt_orig, filt))

            return df

    def get_all_groups(self, df):
        """
        Generator to get all possible allowed groups of data

        Args:
            df:

        Returns:

        """

        group_cols = ['row', 'col', 'wrap', 'leg']
        groups = [getattr(self, f) for f in group_cols
                  if hasattr(self, f) and getattr(self, f) is not None]

        for i, (nn, gg) in enumerate(df.groupby(groups)):
            yield i, nn, self.transform(gg.copy())

    def get_box_index_changes(self):
        """
        Make a DataFrame that shows when groups vals change; used for grouping labels

        Args:
            df (pd.DataFrame): grouping values
            num_groups (int): number of unique groups

        Returns:
            new DataFrame with 1's showing where group levels change for each row of df
        """

        # Check for nan columns
        if self.groups is not None:
            for group in self.groups:
                if len(self.df_rc[group].dropna()) == 0:
                    self.groups.remove(group)
                    print('Column "%s" is all NaN and will be excluded from plot' % group)

        # Get the changes df
        if self.groups is None:
            groups = [(None, self.df_rc.copy())]
            self.ngroups = 0
        else:
            groups = self.df_rc.groupby(self.groups)
            self.ngroups = groups.ngroups

        # Order the group labels with natsorting
        gidx = []
        for i, (nn, g) in enumerate(groups):
            gidx += [nn]
        gidx = natsorted(gidx)
        self.indices = pd.DataFrame(gidx)
        self.changes = self.indices.copy()

        # Set initial level to 1
        for col in self.indices.columns:
            self.changes.loc[0, col] = 1

        # Determines values for all other rows
        for i in range(1, self.ngroups):
            for col in self.indices.columns:
                if self.indices[col].iloc[i-1] == self.indices[col].iloc[i]:
                    self.changes.loc[i, col] = 0
                else:
                    self.changes.loc[i, col] = 1

    def get_conf_int(self, df, x, y, **kwargs):
        """
        Calculate and draw confidence intervals around a curve

        Args:
            df:
            x:
            y:
            ax:
            color:
            kw:

        Returns:

        """

        if not self.conf_int:
            return

        if str(self.conf_int).lower() == 'range':
            ymin = df.groupby(x).min()[y]
            self.stat_idx = ymin.index
            self.lcl = ymin.reset_index(drop=True)
            self.ucl = df.groupby(x).max()[y].reset_index(drop=True)

        else:
            if float(self.conf_int) > 1:
                self.conf_int = float(self.conf_int)/100
            stat = pd.DataFrame()
            stat['mean'] = df[[x, y]].groupby(x).mean().reset_index()[y]
            stat['count'] = df[[x, y]].groupby(x).count().reset_index()[y]
            stat['std'] = df[[x, y]].groupby(x).std().reset_index()[y]
            stat['sderr'] = stat['std'] / np.sqrt(stat['count'])
            stat['ucl'] = np.nan
            stat['lcl'] = np.nan
            for irow, row in stat.iterrows():
                if row['std'] == 0:
                    conf = [0, 0]
                else:
                    conf = ss.t.interval(self.conf_int, int(row['count'])-1,
                                        loc=row['mean'], scale=row['sderr'])
                stat.loc[irow, 'ucl'] = conf[1]
                stat.loc[irow, 'lcl'] = conf[0]

            self.stat_idx = df.groupby(x).mean().index
            self.lcl = stat['lcl']
            self.ucl = stat['ucl']

    def get_data_range(self, ax, df):
        """
        Determine the min/max values for a given axis based on user inputs

        Args:
            axis (str): x, x2, y, y2, z
            df (pd.DataFrame): data table to use for range calculation

        Returns:
            min, max tuple
        """

        if not hasattr(self, ax) or getattr(self, ax) is None:
            return None, None
        #elif len([f for f in getattr(self, ax) if str(f) not in df.columns]) > 0:
        #    return None, None
        else:
            cols = getattr(self, ax)

        # Heatmap special case
        if self.plot_func == 'plot_heatmap':
            if getattr(self, ax) == ['Column']:
                vmin = min([f for f in df.columns if type(f) is int])
                vmax = max([f for f in df.columns if type(f) is int])
            elif getattr(self, ax) == ['Row']:
                vmin = min([f for f in df.index if type(f) is int])
                vmax = max([f for f in df.index if type(f) is int])
            elif getattr(self, ax) == ['Value'] and self.auto_cols:
                vmin = df.min().min()
                vmax = df.max().max()
            elif ax != 'z':
                vmin = 0
                vmax = len(df[getattr(self, ax)].drop_duplicates())
            else:
                vmin = df[getattr(self, ax)].min().iloc[0]
                vmax = df[getattr(self, ax)].max().iloc[0]
            if getattr(self, '%smin' % ax):
                vmin = getattr(self, '%smin' % ax)
            if getattr(self, '%smax' % ax):
                vmax = getattr(self, '%smax' % ax)
            if type(vmin) is str:
                vmin = None
            if type(vmax) is str:
                vmax = None
            return vmin, vmax

        # Groupby for stats
        if self.stat is not None and 'only' in self.stat:
            stat_groups = []
            vals_2_chk = ['stat_val', 'leg', 'col', 'row', 'wrap']
            for v in vals_2_chk:
                if getattr(self, v) is not None:
                    stat_groups += getattr(self, v)

        # Account for any applied stats
        if self.stat is not None and 'only' in self.stat \
                and 'median' in self.stat:
            df = df.groupby(stat_groups).median().reset_index()
        elif self.stat is not None and 'only' in self.stat:
            df = df.groupby(stat_groups).mean().reset_index()

        # Get the dataframe values for this axis
        dfax = df[cols]

        # Calculate actual min / max vals for the axis
        if self.ax_scale in ['log%s' % ax, 'loglog', 'semilog%s' % ax]:
            axmin = dfax[dfax > 0].stack().min()
            axmax = dfax.stack().max()
            axdelta = np.log10(axmax)-np.log10(axmin)
        else:
            axmin = dfax.stack().min()
            axmax = dfax.stack().max()
            axdelta = axmax-axmin
        if axdelta <= 0:
            axmin -= 0.1*axmin
            axmax += 0.1*axmax

        # Check user-specified min values
        vmin = getattr(self, '%smin' % ax)
        if vmin is not None and 'iqr' in str(vmin).lower():
            factor = str(vmin).split('*')
            if len(factor) == 1:
                factor = 1
            else:
                factor = float(factor[0])
            if 'box' not in self.plot_func or self.groups is None:
                q1 = dfax.quantile(0.25).min()
                q3 = dfax.quantile(0.75).max()
                iqr = factor*(q3 - q1)
                vmin = q1 - iqr
            else:
                q1 = df.groupby(self.groups) \
                          .quantile(0.25)[cols].reset_index()
                q3 = df.groupby(self.groups) \
                         .quantile(0.75)[cols].reset_index()
                iqr = factor*(q3[cols] - q1[cols])
                vmin = (q1[cols] - iqr[cols]).min().iloc[0]
        elif vmin is not None and 'q' in str(vmin).lower():
            xq = float(str(vmin).lower().replace('q', ''))/100
            if self.groups is None:
                vmin = dfax.quantile(xq).min()
            else:
                vmin = df.groupby(self.groups) \
                        .quantile(xq)[cols].min().iloc[0]
        elif vmin is not None:
            vmin = vmin
        elif getattr(self, 'ax_limit_padding_%s_min' % ax) is not None:
            if self.ax_scale in ['log%s' % ax, 'loglog',
                                 'semilog%s' % ax]:
                axmin = np.log10(axmin) - \
                        getattr(self, 'ax_limit_padding_%s_min' % ax) * axdelta
                vmin = 10**axmin
            else:
                axmin -= getattr(self, 'ax_limit_padding_%s_min' % ax) * axdelta
                vmin = axmin
        else:
            vmin = None

        # Check user-specified max values
        vmax = getattr(self, '%smax' % ax)
        if vmax is not None and 'iqr' in str(vmax).lower():
            factor = str(vmax).split('*')
            if len(factor) == 1:
                factor = 1
            else:
                factor = float(factor[0])
            if 'box' not in self.plot_func or self.groups is None:
                q1 = dfax.quantile(0.25).min()
                q3 = dfax.quantile(0.75).max()
                iqr = factor*(q3 - q1)
                vmax = q3 + iqr
            else:
                q1 = df.groupby(self.groups) \
                          .quantile(0.25)[cols].reset_index()
                q3 = df.groupby(self.groups) \
                         .quantile(0.75)[cols].reset_index()
                iqr = factor*(q3[cols] - q1[cols])
                vmax = (q3[cols] + iqr[cols]).max().iloc[0]  # should this be referred to median?
        elif vmax is not None and 'q' in str(vmax).lower():
            xq = float(str(vmax).lower().replace('q', ''))/100
            if self.groups is None:
                vmax = dfax.quantile(xq).max()
            else:
                vmax = df.groupby(self.groups) \
                        .quantile(xq)[cols].max().iloc[0]
        elif vmax is not None:
            vmax = vmax
        elif getattr(self, 'ax_limit_padding_%s_max' % ax) is not None:
            if self.ax_scale in ['log%s' % ax, 'loglog',
                                 'semilog%s' % ax]:
                axmax = np.log10(axmax) + \
                        getattr(self, 'ax_limit_padding_%s_max' % ax) * axdelta
                vmax = 10**axmax
            else:
                axmax += getattr(self, 'ax_limit_padding_%s_max' % ax) * axdelta
                vmax = axmax
        else:
            vmax = None

        return vmin, vmax

    def get_data_ranges(self, ir, ic):
        """
        Get the data ranges

        Args:
            ir (int): subplot row index
            ic (int): subplot col index

        """

        df_fig = self.df_fig.copy()
        df_rc = self.df_rc.copy()

        if self.auto_scale:
            # Filter down by axis limits that have been specified by the user
            limits = ['xmin', 'xmax', 'x2min', 'x2max', 'ymin', 'ymax',
                      'y2min', 'y2max']

            fixed = [f for f in limits if getattr(self, f) is not None]

            for f in fixed:
                ax = f[0:-3]
                side = f[-3:]
                if '2' in ax and (self.twin_x or self.twin_y):
                    ax = [getattr(self, ax[0])[1]]
                elif self.twin_x and ax == 'y' or self.twin_y and ax == 'x':
                    ax = [getattr(self, ax[0])[0]]
                else:
                    ax = getattr(self, ax)

                for axx in ax:
                    # Adjust the dataframe by the limits
                    if type(getattr(self, f)) is str:
                        continue
                    if side == 'min':
                        df_fig = df_fig[df_fig[axx] >= getattr(self, f)]
                        df_rc = df_rc[df_rc[axx] >= getattr(self, f)]
                    else:
                        df_fig = df_fig[df_fig[axx] <= getattr(self, f)]
                        df_rc = df_rc[df_rc[axx] <= getattr(self, f)]

        # Iterate over axis
        axs = ['x', 'x2', 'y', 'y2', 'z']
        for ax in axs:
            if ax == 'z':
                df_fig = self.df_fig.copy()
                df_rc = self.df_rc.copy()
            if ax == 'y' and self.plot_func == 'plot_hist':
                self.get_data_ranges_hist(ir, ic)
                continue
            if getattr(self, 'share_%s' % ax) and ir == 0 and ic == 0:
                vals = self.get_data_range(ax, df_fig)
                self.ranges[ir, ic]['%smin' % ax] = vals[0]
                self.ranges[ir, ic]['%smax' % ax] = vals[1]
            elif self.share_row:
                vals = self.get_data_range(ax,
                    df_fig[df_fig[self.row[0]] == self.row_vals[ir]])
                self.ranges[ir, ic]['%smin' % ax] = vals[0]
                self.ranges[ir, ic]['%smax' % ax] = vals[1]
            elif self.share_col:
                vals = self.get_data_range(ax,
                    df_fig[df_fig[self.col[0]] == self.col_vals[ic]])
                self.ranges[ir, ic]['%smin' % ax] = vals[0]
                self.ranges[ir, ic]['%smax' % ax] = vals[1]
            elif not getattr(self, 'share_%s' % ax):
                vals = self.get_data_range(ax, df_rc)
                self.ranges[ir, ic]['%smin' % ax] = vals[0]
                self.ranges[ir, ic]['%smax' % ax] = vals[1]
            elif self.wrap is not None and self.wrap == 'y' or self.wrap == 'x':
                vals = self.get_data_range(ax, df_rc)
                self.ranges[ir, ic]['%smin' % ax] = vals[0]
                self.ranges[ir, ic]['%smax' % ax] = vals[1]
            else:
                self.ranges[ir, ic]['%smin' % ax] = \
                    self.ranges[0, 0]['%smin' % ax]
                self.ranges[ir, ic]['%smax' % ax] = \
                    self.ranges[0, 0]['%smax' % ax]

    def get_data_ranges_hist(self, ir, ic):
        """
        Get the data ranges

        Args:
            ir (int): subplot row index
            ic (int): subplot col index

        """

        self.y = ['Counts']
        df_hist = pd.DataFrame()

        if self.share_y and ir == 0 and ic == 0:
            for iir, iic, df_rc in self.get_rc_subset(self.df_fig):
                if len(df_rc) == 0:
                    break
                for iline, df, x, y, z, leg_name, twin in self.get_plot_data(df_rc):
                    counts = np.histogram(df[self.x[0]], bins=self.bins, normed=self.norm)[0]
                    df_hist = pd.concat([df_hist, pd.DataFrame({self.y[0]: counts})])
            vals = self.get_data_range('y', df_hist)
            self.ranges[ir, ic]['ymin'] = vals[0]
            self.ranges[ir, ic]['ymax'] = vals[1]
        elif self.share_row:
            for iir, iic, df_rc in self.get_rc_subset(self.df_fig):
                df_row = df_rc[df_rc[self.row[0]] == self.row_vals[ir]].copy()
                for iline, df, x, y, z, leg_name, twin in self.get_plot_data(df_row):
                    counts = np.histogram(df[self.x[0]], bins=self.bins, normed=self.norm)[0]
                    df_hist = pd.concat([df_hist, pd.DataFrame({self.y[0]: counts})])
            vals = self.get_data_range('y', df_hist)
            self.ranges[ir, ic]['ymin'] = vals[0]
            self.ranges[ir, ic]['ymax'] = vals[1]
        elif self.share_col:
            for iir, iic, df_rc in self.get_rc_subset(self.df_fig):
                df_col = df_rc[df_rc[self.col[0]] == self.col_vals[ic]]
                for iline, df, x, y, z, leg_name, twin in self.get_plot_data(df_col):
                    counts = np.histogram(df[self.x[0]], bins=self.bins, normed=self.norm)[0]
                    df_hist = pd.concat([df_hist, pd.DataFrame({self.y[0]: counts})])
            vals = self.get_data_range('y', df_hist)
            self.ranges[ir, ic]['ymin'] = vals[0]
            self.ranges[ir, ic]['ymax'] = vals[1]
        elif not self.share_y:
            for iline, df, x, y, z, leg_name, twin in self.get_plot_data(self.df_rc):
                counts = np.histogram(df[self.x[0]], bins=self.bins, normed=self.norm)[0]
                df_hist = pd.concat([df_hist, pd.DataFrame({self.y[0]: counts})])
            vals = self.get_data_range('y', df_hist)
            self.ranges[ir, ic]['ymin'] = vals[0]
            self.ranges[ir, ic]['ymax'] = vals[1]
        else:
            self.ranges[ir, ic]['ymin'] = self.ranges[0, 0]['ymin']
            self.ranges[ir, ic]['ymax'] = self.ranges[0, 0]['ymax']
        self.y = None

    def get_df_figure(self):
        """
        Generator to subset the main DataFrame based on fig_item grouping

        Args:
            fig_item (str): figure grouping value
            kw (dict): kwargs dict

        Returns:
            DataFrame subset
        """

        self.get_fig_groupings()

        if not self.fig_vals:
            self.get_legend_groupings(self.df_all)
            self.get_rc_groupings(self.df_all)
            self.df_fig = self.df_all
            for ir, ic, df_rc in self.get_rc_subset(self.df_fig, True):
                continue
            yield None, None, None, self.df_fig

        else:
            for ifig, fig_val in enumerate(self.fig_vals):
                if type(fig_val) is tuple:
                    for ig, gg in enumerate(fig_val):
                        self.df_fig = self.df_all[self.df_all[self.fig_groups[ig]] == gg].copy()
                elif self.fig_groups is not None:
                    if type(self.fig_groups) is list:
                        self.df_fig = self.df_all[self.df_all[self.fig_groups[0]] == fig_val].copy()
                    else:
                        self.df_fig = self.df_all[self.df_all[self.fig_groups] == fig_val].copy()
                else:
                    self.df_fig = self.df_all

                self.get_legend_groupings(self.df_fig)
                self.get_rc_groupings(self.df_fig)

                for ir, ic, df_rc in self.get_rc_subset(self.df_fig, True):
                    continue
                yield ifig, fig_val, self.fig, self.df_fig

        self.df_fig = None

    def get_fig_groupings(self):
        """
        Determine the figure grouping levels
        """

        if self.fig:
            self.fig_vals = list(self.df_all.groupby(self.fig).groups.keys())

    def get_fit_data(self, ir, ic, df, x, y):
        """
        Make columns of fitted data

        Args:
            df (pd.DataFrame): main DataFrame
            x (str): x-column name
            y (str): y-column name

        Returns:
            updated DataFrame and rsq (for poly fit only)
        """

        df2 = df.copy()
        df['%s Fit' % x] = np.nan
        df['%s Fit' % y] = np.nan

        if not self.fit:
            return df, np.nan

        if self.fit == True or type(self.fit) is int:

            if type(self.fit_range_x) is list:
                df2 = df2[(df2[x] >= self.fit_range_x[0]) & \
                          (df2[x] <= self.fit_range_x[1])].copy()
            elif type(self.fit_range_y) is list:
                df2 = df2[(df2[y] >= self.fit_range_y[0]) & \
                          (df2[y] <= self.fit_range_y[1])].copy()
            else:
                df2 = df2.copy()

            xx = np.array(df2[x])
            yy = np.array(df2[y])

            # Fit the polynomial
            coeffs = np.polyfit(xx, yy, int(self.fit))

            # Find R^2
            yval = np.polyval(coeffs, xx)
            ybar = yy.sum()/len(yy)
            ssreg = np.sum((yval-ybar)**2)
            sstot = np.sum((yy-ybar)**2)
            rsq = ssreg/sstot

            # Add fit line
            df['%s Fit' % x] = np.linspace(self.ranges[ir, ic]['xmin'],
                                           self.ranges[ir, ic]['xmax'], len(df))
            df['%s Fit' % y] = np.polyval(coeffs, df['%s Fit' % x])

            return df, coeffs, rsq

        if str(self.fit).lower() == 'spline':

            # PUT SPLINE CODE HERE

            return df, [], np.nan

    def get_legend_groupings(self, df):
        """
        Determine the legend groupings

        Args:
            df (pd.DataFrame):  data being plotted

        Returns:
            updated kwargs dict
        """

        if self.legend == True and self.twin_x \
                or self.legend == True and len(self.y) > 1:
            self.legend_vals = self.y
            self.nleg = len(self.y)
            return
        elif self.legend == True and self.twin_y:
            self.legend_vals = self.x
            self.nleg = len(self.x)
            return

        if not self.legend:
            return

        leg_all = []

        if self.legend == True:
            self.legend = None  # no option for legend here so disable
            return

        if self.legend:
            if type(self.legend) is list:
                for ileg, leg in enumerate(self.legend):
                    if ileg == 0:
                        temp = df[leg].copy()
                    else:
                        temp = temp.map(str) + ' | ' + df[leg].map(str)
                self.legend = ' | '.join(self.legend)
                df[self.legend] = temp
            legend_vals = \
                natsorted(list(df.groupby(self.legend).groups.keys()))
            self.nleg = len(legend_vals)
        else:
            legend_vals = [None]
            self.nleg = 0

        for leg in legend_vals:
            if not self.x:
                selfx = [None]
            else:
                selfx = self.x
            if not self.y:
                selfy = [None]
            else:
                selfy = self.y
            for xx in selfx:
                for yy in selfy:
                    leg_all += [(leg, xx, yy)]

        leg_df = pd.DataFrame(leg_all, columns=['Leg', 'x', 'y'])

        # if leg specified
        if not (leg_df.Leg==None).all():
            leg_df['names'] = list(leg_df.Leg)

        # if more than one y axis and leg specified
        if self.wrap == 'y' or self.wrap == 'x':
            leg_df = leg_df.drop(self.wrap, axis=1).drop_duplicates()
            leg_df[self.wrap] = self.wrap

        elif len(leg_df.y.unique()) > 1 and not (leg_df.Leg==None).all() and len(leg_df.x.unique()) == 1:
            leg_df['names'] = leg_df.Leg.map(str) + ' | ' + leg_df.y.map(str)

        # elif self.twin_x:
        #     leg_df['names'] = leg_df.y

        # if more than one x and leg specified
        if 'names' not in leg_df.columns:
            leg_df['names'] = leg_df.x
        elif len(leg_df.x.unique()) > 1 and not self.twin_x:
            leg_df['names'] = \
                leg_df['names'].map(str) + ' | ' + leg_df.y.map(str) + ' / ' + leg_df.x.map(str)
        # elif self.twin_x:
        #     leg_df['names'] = leg_df.x.map(str)

        new_index = natsorted(leg_df['names'])
        leg_df = leg_df.set_index('names')
        # leg_df = leg_df.loc[new_index].reset_index() # why is this here??
        self.legend_vals = leg_df.reset_index()

    def get_plot_data(self, df):
        """
        Generator to subset into discrete sets of data for each curve

        Args:
            df (pd.DataFrame): main DataFrame

        Returns:
            subset
        """

        if type(self.legend_vals) != pd.DataFrame:
            lenx = 1 if not self.x else len(self.x)
            leny = 1 if not self.y else len(self.y)
            vals = pd.DataFrame({'x': self.x if not self.x else self.x*leny,
                                 'y': self.y if not self.y else self.y*lenx})

            for irow, row in vals.iterrows():
                # Set twin ax status
                twin = False
                if (row['x'] != vals.loc[0, 'x'] and self.twin_y) \
                        or (row['y'] != vals.loc[0, 'y'] and self.twin_x):
                    twin = True
                if self.legend_vals is not None and self.twin_y:
                    leg = row['x']
                elif self.legend_vals is not None:
                    leg = row['y']
                else:
                    leg = None

                yield irow, df, row['x'], row['y'], \
                      None if self.z is None else self.z[0], leg, twin

        else:
            for irow, row in self.legend_vals.iterrows():
                # Fix unique wrap vals
                if self.wrap == 'y' or self.wrap == 'x':
                    wrap_col = list(set(df.columns) & set(getattr(self, self.wrap)))[0]
                    df = df.rename(columns={self.wrap: wrap_col})
                    row[self.wrap] = wrap_col

                # Subset by legend value
                if row['Leg'] is not None:
                    df2 = df[df[self.legend]==row['Leg']].copy()

                # Filter out all nan data
                if row['x'] and row['x'] in df2.columns and len(df2[row['x']].dropna()) == 0 \
                        or row['y'] and row['y'] in df2.columns and len(df2[row['y']].dropna()) == 0:
                    continue

                # Set twin ax status
                twin = False
                if (row['x'] != self.legend_vals.loc[0, 'x'] and self.twin_y) \
                        or (row['y'] != self.legend_vals.loc[0, 'y'] and self.twin_x):
                    twin = True

                yield irow, df2, row['x'], row['y'], \
                      None if self.z is None else self.z[0], row['names'], twin

    def get_rc_groupings(self, df):
        """
        Determine the row and column or wrap grid groupings

        Args:
            df (pd.DataFrame):  data being plotted; usually a subset of
                self.df_all
        """

        # Set up wrapping (wrap option overrides row/col)
        if self.wrap:
            if self.wrap_vals is None:
                self.wrap_vals = \
                    natsorted(list(df.groupby(self.wrap).groups.keys()))
            if self.ncols == 0:
                rcnum = int(np.ceil(np.sqrt(len(self.wrap_vals))))
            else:
                rcnum = self.ncols if self.ncols <= len(self.wrap_vals) \
                        else len(self.wrap_vals)
            self.ncol = rcnum
            self.nrow = int(np.ceil(len(self.wrap_vals)/rcnum))
            self.nwrap = len(self.wrap_vals)

        # Non-wrapping option
        else:
            # Set up the row grouping
            if self.col:
                self.col_vals = \
                    natsorted(list(df.groupby(self.col).groups.keys()))
                self.ncol = len(self.col_vals)

            if self.row:
                self.row_vals = \
                    natsorted(list(df.groupby(self.row).groups.keys()))
                self.nrow = len(self.row_vals)

        if self.ncol == 0:
            raise GroupingError('Cannot make subplot(s): '
                                'number of columns is 0')
        if self.nrow == 0:
            raise GroupingError('Cannot make subplot(s): '
                                'number of rows is 0')

        self.ranges = np.array([[None]*self.ncol]*self.nrow)
        for ir in range(0, self.nrow):
            for ic in range(0, self.ncol):
                self.ranges[ir, ic] = {}

    def get_rc_subset(self, df, ranges=False):
        """
        Subset the data by the row/col values

        Args:
            df (pd.DataFrame): main DataFrame

        Returns:
            subset DataFrame
        """

        df = df.copy()

        transform = any([self.xtrans, self.x2trans, self.ytrans, self.y2trans,
                         self.ztrans])

        for ir in range(0, self.nrow):
            for ic in range(0, self.ncol):
                if self.wrap is not None:
                    if ir*self.ncol + ic > self.nwrap-1:
                        self.df_rc = pd.DataFrame()
                    elif self.wrap == 'y':
                        self.y = utl.validate_list(self.wrap_vals[ic + ir * self.ncol])
                        cols = (utl.validate_list(self.x) if self.x is not None else []) + \
                               (utl.validate_list(self.y) if self.y is not None else []) + \
                               (utl.validate_list(self.groups) if self.groups is not None else []) + \
                               (utl.validate_list(self.legend) if self.legend not in [None, True, False] else [])
                        self.df_rc = df[cols]
                    elif self.wrap == 'x':
                        self.x = utl.validate_list(self.wrap_vals[ic + ir * self.ncol])
                        cols = (utl.validate_list(self.x) if self.x is not None else []) + \
                               (utl.validate_list(self.y) if self.y is not None else []) + \
                               (utl.validate_list(self.groups) if self.groups is not None else []) + \
                               (utl.validate_list(self.legend) if self.legend is not None else [])
                        if self.plot_func == 'plot_hist':
                            cols = [f for f in cols if f != 'Counts']
                        self.df_rc = df[cols]
                    else:
                        wrap = dict(zip(self.wrap,
                                    utl.validate_list(self.wrap_vals[ir*self.ncol + ic])))
                        self.df_rc = df.loc[(df[list(wrap)] == pd.Series(wrap)).all(axis=1)].copy()
                else:
                    if self.row is not None and self.col is not None:
                        row = self.row_vals[ir]
                        col = self.col_vals[ic]
                        self.df_rc = df[(df[self.row[0]]==row) &
                                        (df[self.col[0]]==col)].copy()
                    elif self.row and not self.col:
                        row = self.row_vals[ir]
                        self.df_rc = df[(df[self.row[0]]==row)].copy()
                    elif self.col and not self.row:
                        col = self.col_vals[ic]
                        self.df_rc = df[(df[self.col[0]]==col)].copy()
                    else:
                        self.df_rc = df

                # Perform any axis transformations
                if transform:
                    self.df_rc = self.transform(self.df_rc)

                # Reshaping
                if self.plot_func == 'plot_heatmap':
                    if self.pivot:
                        # Reshape if input dataframe is stacked
                        self.df_rc = pd.pivot_table(self.df_rc, values=self.z[0],
                                                    index=self.y[0], columns=self.x[0])
                    cols = natsorted(self.df_rc.columns)
                    self.df_rc = self.df_rc[cols]
                    # Set limits
                    if not self.xmin:
                        self.xmin = -0.5
                    if not self.xmax:
                        self.xmax = len(self.df_rc.columns) - 0.5
                    if self.ymin is not None and self.ymax is not None \
                            and self.ymin < self.ymax:
                        ymin = self.ymin
                        self.ymin = self.ymax
                        self.ymax = ymin
                    if not self.ymax:
                        self.ymax = -0.5
                    if not self.ymin:
                        self.ymin = len(self.df_rc) - 0.5
                    if self.x == ['Column'] and self.auto_cols:
                        self.df_rc = self.df_rc[[f for f in self.df_rc.columns
                                                    if f >= self.xmin]]
                        self.df_rc = self.df_rc[[f for f in self.df_rc.columns
                                                    if f <= self.xmax]]
                    if self.y == ['Row'] and self.auto_cols:
                        self.df_rc = self.df_rc.loc[[f for f in self.df_rc.index
                                                        if f >= self.ymax]]
                        self.df_rc = self.df_rc.loc[[f for f in self.df_rc.index
                                                         if f <= self.ymin]]
                    dtypes = [int, np.int32, np.int64]
                    if self.df_rc.index.dtype in dtypes and list(self.df_rc.index) != \
                            [f + self.df_rc.index[0] for f in range(0, len(self.df_rc.index))]:
                        self.df_rc.index = self.df_rc.index.astype('O')
                    if self.df_rc.columns.dtype in dtypes and list(self.df_rc.columns) != \
                            [f + self.df_rc.columns[0] for f in range(0, len(self.df_rc.columns))]:
                        self.df_rc.columns = self.df_rc.columns.astype('O')

                # Deal with empty dfs
                if len(self.df_rc) == 0:
                    self.df_rc = pd.DataFrame()

                # Calculate axis ranges
                if ranges:
                    self.get_data_ranges(ir, ic)

                # Get boxplot changes DataFrame
                if 'box' in self.plot_func and len(self.df_rc) > 0:  # think we are doing this twice
                    self.get_box_index_changes()
                    self.ranges[ir, ic]['xmin'] = 0.5
                    self.ranges[ir, ic]['xmax'] = len(self.changes) + 0.5

                # Yield the subset
                yield ir, ic, self.df_rc

        self.df_sub = None

    def get_stat_data(self, df, x, y):
        """
        Get a stat subset from input data

        Args:
            df (pd.DataFrame): input data
            x (str): x-column name
            y (str): y-column name

        """

        if not self.stat:
            return pd.DataFrame()

        df_stat = df.groupby(x if not self.stat_val else self.stat_val)
        try:
            return getattr(df_stat, self.stat)().reset_index()
        except:
            print('stat "%s" is not supported...skipping stat calculation' % self.stat)
            return None

    def see(self):
        """
        Prints a readable list of class attributes
        """

        df = pd.DataFrame({'Attribute':list(self.__dict__.copy().keys()),
             'Name':[str(f) for f in self.__dict__.copy().values()]})
        df = df.sort_values(by='Attribute').reset_index(drop=True)

        return df

    def transform(self, df):
        """
        Transform x, y, or z data

        Args:
            df (pd.DataFrame): current DataFrame
            x (str): x column name
            y (list): y column names
            z (str): z column name

        Returns:
            updated DataFrame
        """

        df = df.copy()

        axis = ['x', 'y', 'z']

        for ax in axis:
            vals = getattr(self, ax)
            if not vals:
                continue
            for val in vals:
                if getattr(self, '%strans' % ax) == 'abs':
                    df.loc[:, val] = abs(df[val])
                elif getattr(self, '%strans' % ax) == 'negative' \
                        or getattr(self, '%strans' % ax) == 'neg':
                    df.loc[:, val] = -df[val]
                elif getattr(self, '%strans' % ax) == 'inverse' \
                        or getattr(self, '%strans' % ax) == 'inv':
                    df.loc[:, val] = 1/df[val]
                elif (type(getattr(self, '%strans' % ax)) is tuple \
                        or type(getattr(self, '%strans' % ax)) is list) \
                        and getattr(self, '%strans' % ax)[0] == 'pow':
                    df.loc[:, val] = df[val]**getattr(self, '%strans' % ax)[1]
                elif getattr(self, '%strans' % ax) == 'flip':
                    maxx = df.loc[:, val].max()
                    df.loc[:, val] -= maxx
                    df.loc[:, val] = abs(df[val])

        return df
