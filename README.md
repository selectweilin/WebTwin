# Website Extractor

![Website Extractor Banner](https://img.shields.io/badge/Website%20Extractor-Advanced-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

Website Extractor is a powerful Python-based tool that allows you to download and archive entire websites with a single click. This application extracts HTML, CSS, JavaScript, images, fonts, and other assets from any website, making it ideal for:

- Creating pixel-perfect copies of any website online
- Training AI agents with real-world web content
- Studying website structure and design
- Extracting UI components for design inspiration
- Archiving web content for research
- Learning web development techniques

The application features advanced rendering capabilities using Selenium, allowing it to properly extract assets from modern JavaScript-heavy websites and single-page applications.

![App Architecture Overview](https://raw.githubusercontent.com/username/website-extractor/main/docs/app_architecture_overview.png)

## Features

- **Advanced Rendering**: Uses Selenium with Chrome WebDriver to render JavaScript-heavy sites
- **Comprehensive Asset Extraction**: Downloads HTML, CSS, JavaScript, images, fonts, and more
- **Metadata Extraction**: Captures site metadata, OpenGraph tags, and structured data
- **UI Component Analysis**: Identifies and extracts UI components like headers, navigation, cards, etc.
- **Organized Output**: Creates a well-structured ZIP file with assets organized by type
- **Responsive Design**: Works with both desktop and mobile websites
- **CDN Support**: Handles assets from various Content Delivery Networks
- **Modern Framework Support**: Special handling for React, Next.js, Angular, and Tailwind CSS

## Advanced Use Cases

### Pixel-Perfect Website Copies
Create exact replicas of websites for study, testing, or inspiration. The advanced rendering engine ensures even complex layouts and JavaScript-driven designs are faithfully reproduced.

### AI Agent Training
Extract websites to create high-quality training data for your AI agents:
- Feed the structured content to AI models to improve their understanding of web layouts
- Train AI assistants on real-world UI components and design patterns
- Create diverse datasets of web content for machine learning projects

### Cursor IDE Integration
Website Extractor works seamlessly with Cursor IDE:
- Extract a website and open it directly in Cursor for code analysis
- Edit the extracted code with Cursor's AI-powered assistance
- Use the components as reference for your own projects
- Ask Cursor to analyze the site's structure and styles to apply similar patterns to your work

### Design Inspiration & Reference
Upload the extracted folder to your current project and:
- Ask Cursor to reference its style when building new pages
- Study professional UI implementations
- Extract specific components for reuse in your own projects
- Learn modern CSS techniques from production websites

## Installation

### Prerequisites

- Python 3.7+
- Chrome/Chromium browser (for advanced rendering)
- Git

### Using Cursor (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/sirioberati/website-extractor.git
   cd website-extractor
   ```

2. Open the project in Cursor IDE:
   ```bash
   cursor .
   ```

3. Create a virtual environment (within Cursor's terminal):
   ```bash
   python -m venv venv
   ```

4. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`

5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/sirioberati/website-extractor.git
   cd website-extractor
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Activate your virtual environment (if not already activated)

2. Run the application:
   ```bash
   python app.py
   ```

3. Open your browser and navigate to:
   ```
   http://127.0.0.1:5001
   ```

4. Enter the URL of the website you want to extract

5. Check "Use Advanced Rendering (Selenium)" for JavaScript-heavy websites

6. Click "Extract Website" and wait for the download to complete

### Using Advanced Rendering

The advanced rendering option uses Selenium with Chrome WebDriver to:
- Execute JavaScript
- Render dynamic content
- Scroll through the page to trigger lazy loading
- Click on UI elements to expose hidden content
- Extract resources loaded by JavaScript frameworks

This option is recommended for modern websites, especially those built with React, Angular, Vue, or other JavaScript frameworks.

### Using with Cursor IDE

After extracting a website:

1. Unzip the downloaded file to a directory
2. Open with Cursor IDE:
   ```bash
   cursor /path/to/extracted/website
   ```
3. Explore the code structure and assets
4. Ask Cursor AI to analyze the code with prompts like:
   - "Explain the CSS structure of this website"
   - "How can I implement a similar hero section in my project?"
   - "Analyze this navigation component and create a similar one for my React app"

## Architecture

The application is built with a modular architecture:

1. **Flask Web Server**: Provides the user interface and API
2. **HTTP Client**: Makes requests to fetch website content
3. **Selenium Renderer**: Optional component for JavaScript rendering
4. **Content Parser**: Analyzes HTML to extract assets and structure
5. **Asset Downloader**: Downloads all discovered assets
6. **ZIP Creator**: Packages everything for download

For more details, see [app_architecture.md](app_architecture.md).

## Limitations

- Some websites implement anti-scraping measures that may block extraction
- Content requiring authentication may not be accessible
- Very large websites may time out or require multiple extraction attempts
- Some CDN-specific URL formats may fail to download (especially those with transformation parameters)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Created by Sirio Berati

- Instagram: [@heysirio](https://instagram.com/heysirio)
- Instagram: [@siriosagents](https://instagram.com/siriosagents)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- This project uses [Flask](https://flask.palletsprojects.com/) for the web framework
- [Selenium](https://www.selenium.dev/) for advanced rendering
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing
- All the open source libraries that made this project possible 