# -*- coding: utf-8 -*-
"""Simple snippet of bokeh real-time streaming using IEX API with TOPS.

Exploring techniques of using bokeh server for real-time streaming of data,
specifically, real-time data streaming of stock prices from a provider, IEX.
Demonstrating the use of bokeh server, capture of streaming data, datetime, and widgets.
Datatime is in the data stream source's timezone.

Original source code:
    https://gist.github.com/zduey/66ed98cf3fc2b161df47c0c08954dc62
    zduey/iex.py

versions used as of April 2020:
    python: 3.8.2
    bokeh: 2.0.1
    pandas: 1.0.3
    pytz: 2019.3

Attributes:
    init():
        Current time in the data stream source timezone.
    update_ticker():
        Module to receive ticker from user.  No error checking.
    get_last_price():
        Retrive ticker price from data stream source.
    update_price():
        Update the data unto the figure.

todo:
    Make the widgets look nicer and placed centrally.
    Ability to display user entered text in upper case.

"""

# stream library
import io
# HTTP library
import requests
# time libraries for time series
from pytz import timezone
from datetime import datetime
from dateutil.parser import parse
# standard libraries
from math import radians
import pandas as pd
# New bokeh methods deprecated original: ResizeTool : replace with WheelZoomTool
#                                        widgetbox : replace with column
# broken in separate lines to fit small viewing areas
from bokeh.models import ColumnDataSource,  DatetimeTickFormatter
from bokeh.models import PanTool, ResetTool, HoverTool, WheelZoomTool, SaveTool
from bokeh.models.widgets import TextInput, Button
from bokeh.plotting import figure, curdoc
from bokeh.layouts import row, column

# constants
TICKER = ""
base = 'https://ws-api.iextrading.com/1.0/'
endpoint = 'tops/last'
set_timezone = 'US/Eastern'

def init():
    """Initialize the figure with current datetime in source's timezone.

    Args:
        None

    Returns:
        datetime in data source's timezone.
    """
    return datetime.now(timezone('UTC')).astimezone(timezone(set_timezone))

def update_ticker():
    """Pass the ticker value from user to internal storage.

    Args:
        None

    Returns:
        None
    """
    global TICKER
    TICKER = ticker_textbox.value
    price_plot.title.text = "IEX Real-Time Price: " + ticker_textbox.value
    data.data = dict(time=[], display_time=[], price=[])
    return

def get_last_price():
    """Get the data for a user specified ticker symbol.

    Data source streamed in JSON format and stored in pandas data frame.
    Extract data and convert to proper data type for display.  The bokeh types are
    of the form float & datetime.

    Args:
        None

    Return:
        time: type datetime: the time stamp of the data
        (df): type series: dataframe returned as a series for hoover tool content
        (price): type float: cast panda series into float
    """
    payload = {
        "format": "csv",
        "symbols": TICKER
    }
    # source stream comes in as a JSON data: see source provider
    # read data stream
    # store in a pandas dataframe
    raw = requests.get(base + endpoint, params=payload)
    raw = io.BytesIO(raw.content)
    prices_df = pd.read_csv(raw, sep=",")

    # convert since epoch time in ms to seconds
    prices_df["time"] = pd.to_datetime(prices_df["time"], unit="ms")
    # convert time to proper timezone based off of original data
    prices_df["time"] = prices_df["time"].dt.tz_localize('UTC').dt.tz_convert(set_timezone)
    # using temp var for return value
    # bokeh will not display a pandas series data, so convert to datatime object
    # convert pandas series to string and parse to datetime
    time = prices_df["time"].to_string()
    # remove index portion, artifact from to_string()
    time = time[1:]
    # convert string to datetime
    time = parse(time)
    # reformat for hoover tool
    prices_df["display_time"] = prices_df["time"].dt.strftime("%Y-%m-%d %H:%M:%S")

    return time, prices_df["display_time"], float(prices_df["price"])

def update_price():
    """Place the data into bokeh for display.

    This code crashes if TICKER is empty upon start.  So check if empty ticker,
    then fill with initial time & $0.00 until user enter ticker symbol.

    Args:
        None

    Returns:
        None
    """
    # need to send valid values of time to .stream
    if  "".__eq__(TICKER):
        time = init()
        display = init()
        new_price = 0.0
    else:
        time, display, new_price = get_last_price()

    new_data = dict(time=[time],
                    display_time=[display],
                    price=[new_price])
    data.stream(new_data, rollover=3600)
    return

# create figure
# option to add: sizing_mode="scale_both"
#   unavailable at time of testing due to using a 4K monitor - might work on non 4K
price_plot = figure(plot_width= 1000,
                    plot_height= 500,
                    x_axis_type='datetime'
                    )

# set up the data for bokeh with empty values - note time in milliseconds
data = ColumnDataSource(dict(time=[], display_time=[], price=[]))

# tools section
hover = HoverTool(tooltips=[
    ("Time", "@display_time"),
    ("IEX Real-Time Price", "@price")
    ])
price_plot.tools=[PanTool(), ResetTool(), SaveTool(), WheelZoomTool()]
price_plot.add_tools(hover)
price_plot.toolbar.logo=None         # no bokeh logo
price_plot.toolbar_location='above' # above figure for better placement

# plot attributes
price_plot.line(x='time', y='price', source=data)
price_plot.xaxis.axis_label = "Time"
price_plot.yaxis.axis_label = "IEX Real-Time Price"
price_plot.title.text = "IEX Real Time Price Security Symbol: " + TICKER
price_plot.x_range.follow = "end"
price_plot.x_range.range_padding = 0

# Required to format the x-axis datetime shown on the plot,
# if omitted, time in bokeh default of micro/milliseconds.
price_plot.xaxis.formatter=DatetimeTickFormatter(
seconds=["%Y-%m-%d %H:%M:%S"],
minsec=["%Y-%m-%d %H:%M:%S"],
minutes=["%Y-%m-%d %H:%M:%S"],
hourmin=["%Y-%m-%d %H:%M:%S"],
hours=["%Y-%m-%d %H:%M:%S"],
days=["%Y-%m-%d %H:%M:%S"],
months=["%Y-%m-%d %H:%M:%S"],
years=["%Y-%m-%d %H:%M:%S"]
)
# Angled display for better reading.
price_plot.xaxis.major_label_orientation=radians(45)

# create widgets - textbox
ticker_textbox = TextInput(placeholder="Ticker")
update = Button(label="Update")
update.on_click(update_ticker)
inputs = row(ticker_textbox, update)

# render on the web page
curdoc().add_root(column(price_plot, row(inputs), width=1600))
curdoc().title = "Real-Time Price Plot from IEX"
curdoc().add_periodic_callback(update_price, 1000)
