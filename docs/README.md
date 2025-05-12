# DeepNext Documentation

This directory contains the GitHub Pages documentation for the DeepNext project. The documentation is built using Jekyll and the Cayman theme.

## Local Development

To run the documentation site locally:

1. Install Jekyll and dependencies:
```bash
gem install jekyll bundler
```

2. Run the local server:
```bash
cd docs
bundle exec jekyll serve
```

3. View the site at http://localhost:4000

## Documentation Structure

- `index.md`: Main landing page
- `_config.yml`: Jekyll configuration
- `assets/`: Images and other assets
- Content pages:
  - `getting-started.md`: Installation and quick start
  - `architecture.md`: System architecture and components
  - `integration.md`: GitHub/GitLab integration
  - `configuration.md`: Configuration options
  - `contributing.md`: Contribution guidelines

## Adding Content

To add new content:
1. Create a new Markdown file
2. Add front matter with layout and title
3. Add link to the new page from the navigation
