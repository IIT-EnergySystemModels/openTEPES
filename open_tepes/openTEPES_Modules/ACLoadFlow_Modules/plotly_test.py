import webbrowser
import plotly.express as px
import plotly.io as pio

# Setting web browser
urL = 'https://www.google.com'
chrome_path = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
webbrowser.get('chrome')

# Making the plot
pio.renderers.default = 'chrome'
gapminder = px.data.gapminder()
fig = px.scatter(gapminder.query('year==2007'), x='gdpPercap', y='lifeExp',
                 size='pop', color='continent', hover_name='country',
                 log_x=True, size_max=60, height=400, width=650, template='plotly_dark')
fig.show()
