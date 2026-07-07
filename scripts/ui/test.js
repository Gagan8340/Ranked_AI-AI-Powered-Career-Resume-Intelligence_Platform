
  let editor = null;
  const currentTemplateId = "{{ template_id }}";
  
  // 1. Fetch data immediately (decoupled from Monaco)
  async function fetchAndRender() {
    try {
      const token = localStorage.getItem("token");
      const headers = { 'Authorization': `Bearer ${token}` };
      
      // Fetch code
      const res = await fetch(`/api/latex/template/${currentTemplateId}`, { headers });
      const data = await res.json();
      
      if (data.error) throw new Error(data.error);
      
      // Try to set code in Monaco, or fallback
      if (editor) {
        editor.setValue(data.content);
      } else {
        // If Monaco isn't ready or failed, create a fallback textarea
        const container = document.getElementById('editor-container');
        container.innerHTML = '<textarea id="fallback-editor" style="width:100%; height:100%; background:#1e1e1e; color:#d4d4d4; font-family:monospace; padding:10px; border:none; resize:none;"></textarea>';
        document.getElementById('fallback-editor').value = data.content;
      }
      
      // Fetch PDF
      if (data.has_default_pdf) {
        const pdfRes = await fetch(`${data.pdf_url}?t=${new Date().getTime()}`, { headers });
        if (pdfRes.ok) {
          const pdfBlob = await pdfRes.blob();
          await renderPdfBlob(pdfBlob);
        } else {
          const pageContainer = document.getElementById('page-container');
          if (pageContainer) pageContainer.style.display = 'none';
        }
      } else {
        const pageContainer = document.getElementById('page-container');
        if (pageContainer) pageContainer.style.display = 'none';
      }
      
      document.getElementById('recompile-btn').disabled = false;
    } catch (err) {
      console.error(err);
      alert("Error loading template data: " + err.message);
    } finally {
      document.getElementById('editor-loading').style.display = 'none';
    }
  }

  // 2. Try to initialize Monaco
  try {
    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.39.0/min/vs' }});
    require(['vs/editor/editor.main'], function() {
      // Define custom LaTeX grammar for rich syntax highlighting
      monaco.languages.register({ id: 'custom-latex' });
      monaco.languages.setMonarchTokensProvider('custom-latex', {
        tokenizer: {
          root: [
            [/%.*/, 'comment'],
            [/\\[a-zA-Z@]+/, 'keyword'],
            [/\{/, { token: 'delimiter.curly', bracket: '@open', next: '@insideBraces' }],
            [/\[/, { token: 'delimiter.square', bracket: '@open', next: '@insideBrackets' }],
            [/\$.*?\$/, 'string.math'],
            [/-?\d*\.\d+/, 'number.float'],
            [/-?\d+/, 'number'],
          ],
          insideBraces: [
            [/\\[a-zA-Z@]+/, 'keyword'],
            [/[^{}\\]+/, 'string'],
            [/\{/, { token: 'delimiter.curly', bracket: '@open', next: '@push' }],
            [/\}/, { token: 'delimiter.curly', bracket: '@close', next: '@pop' }]
          ],
          insideBrackets: [
            [/\\[a-zA-Z@]+/, 'keyword'],
            [/[^\[\]\\]+/, 'string'],
            [/\[/, { token: 'delimiter.square', bracket: '@open', next: '@push' }],
            [/\]/, { token: 'delimiter.square', bracket: '@close', next: '@pop' }]
          ]
        }
      });
      
      monaco.editor.defineTheme('latex-theme', {
        base: 'vs-dark',
        inherit: true,
        rules: [
          { token: 'keyword', foreground: 'c586c0' }, // Pink
          { token: 'comment', foreground: '6a9955', fontStyle: 'italic' }, // Green
          { token: 'string', foreground: 'ce9178' }, // Orange
          { token: 'number', foreground: 'b5cea8' }, // Light Green
          { token: 'string.math', foreground: 'd16969' } // Red
        ],
        colors: {
          'editor.background': '#1e1e1e'
        }
      });

      editor = monaco.editor.create(document.getElementById('editor-container'), {
        value: '% Loading template content...\n',
        language: 'custom-latex',
        theme: 'latex-theme',
        automaticLayout: true,
        wordWrap: 'on',
        minimap: { enabled: false },
        fontSize: 14,
        fontFamily: "'Fira Code', 'Consolas', 'Courier New', monospace"
      });
      // In case fetch finished before Monaco
      const fallback = document.getElementById('fallback-editor');
      if (fallback) {
        editor.setValue(fallback.value);
        fallback.remove();
      }
    });
  } catch (e) {
    console.warn("Monaco editor failed to load, using fallback.", e);
  }

  // Kick off the fetch immediately
  fetchAndRender();

  // Handle compilation
  document.getElementById('recompile-btn').addEventListener('click', async () => {
    const btn = document.getElementById('recompile-btn');
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Compiling...';
    btn.disabled = true;
    
    try {
      const token = localStorage.getItem("token");
      const headers = { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json' 
      };
      
      let latexCode = "";
      if (editor) {
        latexCode = editor.getValue();
      } else {
        latexCode = document.getElementById('fallback-editor').value;
      }
      
      const res = await fetch('/api/latex/compile', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ latex_code: latexCode })
      });
      
      if (res.ok) {
        const blob = await res.blob();
        await renderPdfBlob(blob);
      } else {
        const errData = await res.json();
        alert('Compilation failed!\n\n' + (errData.error || 'Check console.'));
      }
    } catch (err) {
      alert('An error occurred during compilation: ' + err.message);
    } finally {
      btn.innerHTML = originalHtml;
      btn.disabled = false;
    }
  });
  
  document.addEventListener('keydown', function(e) {
    if ((window.navigator.platform.match("Mac") ? e.metaKey : e.ctrlKey)  && e.keyCode == 83) {
      e.preventDefault();
      document.getElementById('recompile-btn').click();
    }
  }, false);
  // Custom PDF.js rendering logic
  let currentPdfDocument = null;
  async function renderPdfBlob(blob) {
    const url = URL.createObjectURL(blob);
    const loadingTask = pdfjsLib.getDocument(url);
    try {
      currentPdfDocument = await loadingTask.promise;
      const page = await currentPdfDocument.getPage(1);
      
      const viewport = page.getViewport({ scale: 1.5 });
      const canvas = document.getElementById('pdf-canvas');
      const context = canvas.getContext('2d');
      canvas.height = viewport.height;
      canvas.width = viewport.width;
      
      const pageContainer = document.getElementById('page-container');
      if (pageContainer) {
        pageContainer.style.width = viewport.width + 'px';
        pageContainer.style.height = viewport.height + 'px';
        pageContainer.style.display = 'block';
      }

      const renderContext = { canvasContext: context, viewport: viewport };
      await page.render(renderContext).promise;
      
      // Render text layer
      const textContent = await page.getTextContent();
      const textLayer = document.getElementById('pdf-text-layer');
      textLayer.innerHTML = '';
      
      textContent.items.forEach(item => {
        const tx = pdfjsLib.Util.transform(viewport.transform, item.transform);
        const fontHeight = Math.sqrt((tx[2] * tx[2]) + (tx[3] * tx[3]));
        const div = document.createElement('span');
        div.textContent = item.str;
        div.style.left = tx[4] + 'px';
        div.style.top = (tx[5] - fontHeight) + 'px';
        div.style.fontSize = fontHeight + 'px';
        div.style.fontFamily = item.fontName;
        div.style.color = 'transparent';
        div.style.position = 'absolute';
        div.style.whiteSpace = 'pre';
        div.style.cursor = 'text';
        div.style.transformOrigin = '0% 0%';
        textLayer.appendChild(div);
      });
      
    } catch (err) {
      console.error("PDF rendering error: ", err);
      alert("PDF rendering error: " + err.message + "\nCheck console for more details.");
    }
  }

  // Bind double click event for Text Sync
  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('pdf-text-layer').addEventListener('dblclick', () => {
      const selectedText = window.getSelection().toString().trim();
      if (selectedText && editor) {
        // Use Monaco's search API to find the exact text
        const matches = editor.getModel().findMatches(selectedText, true, false, false, null, true);
        if (matches && matches.length > 0) {
          editor.revealLineInCenter(matches[0].range.startLineNumber);
          editor.setSelection(matches[0].range);
        }
      }
    });
  });
