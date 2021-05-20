from bokeh.embed import file_html
from bokeh.io import output_file
from bokeh.layouts import row
from bokeh.plotting import figure, save
from bokeh.resources import CDN

output_file("templates/layout.html")

x = list(range(11))
y0 = x
y1 = [10 - i for i in x]
y2 = [abs(i - 5) for i in x]

# create three plots
s1 = figure(plot_width=250, plot_height=250, background_fill_color="#fafafa")
s1.circle(x, y0, size=12, color="#53777a", alpha=0.8)

s2 = figure(plot_width=250, plot_height=250, background_fill_color="#fafafa")
s2.triangle(x, y1, size=12, color="#c02942", alpha=0.8)

s3 = figure(plot_width=250, plot_height=250, background_fill_color="#fafafa")
s3.square(x, y2, size=12, color="#d95b43", alpha=0.8)

# put the results in a row and save in HTML
html = file_html(row(s1, s2, s3), CDN)

f = open("templates/layout.html", "x")
f.write(html)
f.close()
