from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension
from xml.etree import ElementTree as et
import re
import html

from mkdocs.plugins import BasePlugin
from mkdocs.config import config_options
import logging

log = logging.getLogger(f"mkdocs.plugins.{__name__}")

_cached_patterns = {}

# 默认的 CSS 样式
DEFAULT_CSS = """
:root {
  --md-list-callouts-bg-intensity-light: 0.15;
  --md-list-callouts-bg-intensity-dark: 0.15;
  --md-list-callouts-content-padding-left: 1.2rem;
  --md-list-callouts-symbol-width: 1.25rem;
  --md-list-callouts-border-radius: 0.2rem;
}

.list-callouts {
  padding-left: var(--md-list-callouts-content-padding-left);
  border-radius: var(--md-list-callouts-border-radius);
  position: relative;
  white-space: normal;
  overflow-wrap: break-word;
}

.list-callouts::before {
  font-family: var(--md-code-font);
  font-weight: bold;
  position: absolute;
  left: 0;
  top: 0;
  width: var(--md-list-callouts-symbol-width);
  height: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  text-align: center;
  pointer-events: none;
}


/* & */
.list-callouts-highlight {
  background-color: rgba(246, 217, 67, calc(var(--md-list-callouts-bg-intensity-light) * 100%));
}

.list-callouts-highlight::before {
  content: "&";
  color: rgb(246, 217, 67);
}


/* ? */
.list-callouts-question {
  background-color: rgba(240, 151, 48, calc(var(--md-list-callouts-bg-intensity-light) * 100%));
}

.list-callouts-question::before {
  content: "?";
  color: rgb(240, 151, 48);
}


/* ! */
.list-callouts-warning {
  background-color: rgba(235, 56, 72, calc(var(--md-list-callouts-bg-intensity-light) * 100%));
}

.list-callouts-warning::before {
  content: "!";
  color: rgb(235, 56, 72);
}


/* ~ */
.list-callouts-bookmark {
  background-color: rgba(125, 73, 247, calc(var(--md-list-callouts-bg-intensity-light) * 100%));
}

.list-callouts-bookmark::before {
  content: "~";
  color: rgb(125, 73, 247);
}


/* @ */
.list-callouts-tip {
  background-color: rgba(84, 181, 209, calc(var(--md-list-callouts-bg-intensity-light) * 100%));
}

.list-callouts-tip::before {
  content: "@";
  color: rgb(84, 181, 209);
}


/* $ */
.list-callouts-success {
  background-color: rgba(83, 198, 96, calc(var(--md-list-callouts-bg-intensity-light) * 100%));
}

.list-callouts-success::before {
  content: "$";
  color: rgb(83, 198, 96);
}


/* % */
.list-callouts-quote {
  background-color: rgba(158, 158, 158, calc(var(--md-list-callouts-bg-intensity-light) * 100%));
}

.list-callouts-quote::before {
  content: "%";
  color: rgb(158, 158, 158);
}
"""

class ListCalloutsTreeprocessor(Treeprocessor):
    """
    Process Markdown list items, converting list items that start with specific symbols into styled callouts.

    Symbol mapping defines which symbols are converted to which CSS classes.
    For example, the symbol '!' might be converted to the 'warning' class.
    """

    def __init__(self, symbol_map, insert_default_css=False):
        self.symbol_map = symbol_map
        self.insert_default_css = insert_default_css
        # escaped_symbol_map = {html.escape(k): v for k, v in symbol_map.items()}
        log.debug(f"<ListCallouts> Symbol_map: {symbol_map}")

        escaped_symbols = "".join(re.escape(c) for c in symbol_map.keys())
        log.debug(f"<ListCallouts> Escaped symbols: {escaped_symbols}")

        pattern_key = f"symbols_{escaped_symbols}"

        if pattern_key in _cached_patterns:
            self.pattern = _cached_patterns[pattern_key]
        else:
            self.pattern = re.compile(
                r"^\s*([{}])\s+(.*)".format(escaped_symbols), re.DOTALL
            )
            _cached_patterns[pattern_key] = self.pattern

        log.debug(
            f"<ListCallouts> Initialized ListCalloutsTreeprocessor with symbols_map: {symbol_map}"
        )

    def run(self, root):
        # 如果需要插入默认 CSS，则在文档头部添加 <style> 标签
        if self.insert_default_css:
            self.insert_css(root)
            
        for li in root.iter("li"):
            self.process_li(li)
        return root

    def insert_css(self, root):
        """
        在文档头部插入默认的 CSS 样式
        """
        try:
            # 查找 <head> 标签
            head = None
            for element in root.iter():
                if element.tag == 'head':
                    head = element
                    break
            
            # 如果找到 <head> 标签，在其中添加 <style>
            if head is not None:
                style = et.Element('style')
                style.text = DEFAULT_CSS
                head.append(style)
                log.debug("<ListCallouts> Inserted default CSS into <head>")
            else:
                # 如果没有找到 <head> 标签，则在文档根部添加 <style>
                style = et.Element('style')
                style.text = DEFAULT_CSS
                # 将 style 元素插入到文档的最前面
                root.insert(0, style)
                log.debug("<ListCallouts> Inserted default CSS at document root")
        except Exception as e:
            log.error(f"<ListCallouts> Error inserting CSS: {e}")

    def process_li(self, li):
        try:
            log.debug(
                f"<ListCallouts> Processing list item: {et.tostring(li, encoding='unicode')}"
            )
            content_nodes, list_nodes = self.split_children(li)
            if not content_nodes:
                log.debug("<ListCallouts> No content nodes found in list item")
                return

            text_content = self.get_text_content(content_nodes)
            match = self.pattern.match(text_content)
            if not match:
                log.debug(
                    f"<ListCallouts> No matching symbol found in text content: {text_content}"
                )
                return

            symbol = match.group(1)
            unescaped_symbol = html.unescape(symbol)
            class_name = self.symbol_map.get(unescaped_symbol)
            if not class_name:
                log.debug(f"<ListCallouts> Symbol '{symbol}' not found in symbol_map")
                return

            log.debug(
                f"<ListCallouts> Matched symbol: {symbol}, class_name: {class_name}"
            )

            div = et.Element("div")
            div.set("class", f"list-callouts list-callouts-{class_name}")

            self.remove_symbol(content_nodes, symbol)

            for node in content_nodes:
                div.append(node)

            li.clear()
            li.append(div)
            for node in list_nodes:
                li.append(node)

            log.debug(
                f"<ListCallouts> Processed list item: {et.tostring(li, encoding='unicode')}"
            )
        except Exception as e:
            log.error(f"<ListCallouts> Error processing list item: {e}")

    def split_children(self, li):
        content_nodes = []
        list_nodes = []
        if li.text and li.text.strip():
            text_node = et.Element("span")
            text_node.text = li.text.strip()
            content_nodes.append(text_node)
        for child in li:
            if child.tag in ["ul", "ol"]:
                list_nodes.append(child)
            else:
                content_nodes.append(child)
        return content_nodes, list_nodes

    def get_text_content(self, nodes):
        text = []
        for node in nodes:
            text.append("".join(node.itertext()).strip())
        return " ".join(text).strip()

    def remove_symbol(self, nodes, symbol):
        first = nodes[0] if nodes else None
        if first is None:
            return

        text = self.get_text_content([first])
        match = self.pattern.match(text)
        if not match:
            return

        new_text = match.group(2)
        if first.text:
            first.text = re.sub(self.pattern, r"\2", first.text, count=1)

        if len(first) > 0:
            first.text = new_text + (first.text or "")
        else:
            first.text = new_text


class ListCalloutsExtension(Extension):
    def __init__(self, **kwargs):
        self.config = {
            "symbol_map": [{}, "Mapping of symbols to CSS class suffixes"],
            "insert_default_css": [False, "Whether to insert default CSS styles into the document"]
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        symbol_map = self.getConfig("symbol_map", {})
        insert_default_css = self.getConfig("insert_default_css", False)
        processor = ListCalloutsTreeprocessor(symbol_map, insert_default_css)
        md.treeprocessors.register(processor, "list-callouts", 15)


class ListCalloutsPlugin(BasePlugin):
    config_scheme = {
        (
            "symbol_map",
            config_options.Type(
                dict,
                default={
                    "&": "highlight",
                    "?": "question",
                    "!": "warning",
                    "~": "bookmark",
                    "@": "tip",
                    "$": "success",
                    "%": "quote",
                },
            ),
        ),
        ("insert_default_css", config_options.Type(bool, default=True)),
    }

    def on_config(self, config):
        symbol_map = self.config["symbol_map"]
        insert_default_css = self.config["insert_default_css"]
        config["markdown_extensions"].append(
            ListCalloutsExtension(symbol_map=symbol_map, insert_default_css=insert_default_css)
        )
        return config
