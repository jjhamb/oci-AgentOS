/**
 * Hermes Document Viewer — renders PDF, DOCX, XLSX, images, HTML, and code
 * in the Content tab's preview panel.
 *
 * Uses:
 *   - mammoth.js  (/vendor/mammoth/mammoth.browser.min.js)
 *   - pdfjs-dist  (/vendor/pdfjs-dist/build/pdf.min.mjs)
 *   - xlsx        (/vendor/xlsx/dist/xlsx.full.min.js)
 */
(function () {
  'use strict';

  // ── State ──────────────────────────────────────────────
  let _pdfDoc = null;
  let _pdfRenderTask = null;
  let _xlsxBook = null;
  let _vendorLoaded = {};
  function loadVendor(name, src) {
    return new Promise((resolve, reject) => {
      if (_vendorLoaded[name]) { return resolve(); }
      if (src.endsWith('.mjs')) {
        // Load ES module via dynamic import() from URL
        import(src)
          .then(mod => {
            Object.assign(window, mod);
            _vendorLoaded[name] = true;
            resolve();
          })
          .catch(err => {
            reject(new Error('Failed to load ' + name + ': ' + err.message));
          });
      } else {
        const tag = document.createElement('script');
        tag.src = src;
        tag.onload = () => { _vendorLoaded[name] = true; resolve(); };
        tag.onerror = () => { reject(new Error('Failed to load ' + name)); };
        document.head.appendChild(tag);
      }
    });
  }

  async function ensureAllVendors() {
    await Promise.all([
      loadVendor('mammoth', '/vendor/mammoth/mammoth.browser.min.js'),
      loadVendor('pdfjsLib', '/vendor/pdfjs-dist/build/pdf.min.mjs'),
      loadVendor('XLSX', '/vendor/xlsx/dist/xlsx.full.min.js'),
    ]);
    // Configure pdf.js worker
    if (window.pdfjsLib && window.pdfjsLib.GlobalWorkerOptions) {
      try {
        const workerUrl = URL.createObjectURL(
          new Blob([`import '${location.origin}/vendor/pdfjs-dist/build/pdf.worker.min.mjs';`], { type: 'text/javascript' })
        );
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;
      } catch(e) {
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = '/vendor/pdfjs-dist/build/pdf.worker.min.mjs';
      }
    }
  }

  // ── Helpers ────────────────────────────────────────────
  function el(html) {
    const tpl = document.createElement('div');
    tpl.innerHTML = html.trim();
    return tpl.firstElementChild;
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  // ── PDF Renderer ───────────────────────────────────────
  async function renderPDF(absPath, container) {
    await loadVendor('pdfjsLib', '/vendor/pdfjs-dist/build/pdf.min.mjs');
    // Create a module worker from the .mjs worker file (avoids cross-origin issues)
    if (window.pdfjsLib) {
      try {
        const workerUrl = URL.createObjectURL(
          new Blob(
            [`import '${location.origin}/vendor/pdfjs-dist/build/pdf.worker.min.mjs';`],
            { type: 'text/javascript' }
          )
        );
        if (window.pdfjsLib.GlobalWorkerOptions) {
          window.pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;
        }
      } catch(e) {
        // Fallback: set workerSrc to the direct path
        if (window.pdfjsLib.GlobalWorkerOptions) {
          window.pdfjsLib.GlobalWorkerOptions.workerSrc = '/vendor/pdfjs-dist/build/pdf.worker.min.mjs';
        }
      }
    }

    container.innerHTML = '<div class="doc-loading">Loading PDF…</div>';
    const loading = container.querySelector('.doc-loading');

    try {
      const arrayBuf = await fetch('/api/content/download?path=' + encodeURIComponent(absPath))
        .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.arrayBuffer(); });

      const pdf = await window.pdfjsLib.getDocument({ data: arrayBuf }).promise;
      _pdfDoc = pdf;
      const numPages = pdf.numPages;

      container.innerHTML = '';

      // Toolbar
      const toolbar = el(
        '<div class="pdf-toolbar">' +
          '<div class="pdf-page-info">Page <span class="pdf-cur">1</span> / <span class="pdf-total">' + numPages + '</span></div>' +
          '<div class="pdf-controls">' +
            '<button class="pdf-btn" id="pdfPrev">‹ Prev</button>' +
            '<button class="pdf-btn" id="pdfNext">Next ›</button>' +
          '</div>' +
          '<div class="pdf-zoom">' +
            '<button class="pdf-btn" id="pdfOut">−</button>' +
            '<span class="pdf-zoom-level">100%</span>' +
            '<button class="pdf-btn" id="pdfIn">+</button>' +
          '</div>' +
        '</div>'
      );
      container.appendChild(toolbar);

      const scroller = el('<div class="pdf-scroller"></div>');
      container.appendChild(scroller);

      let currentScale = 1.0;
      let currentPage = 1;

      async function renderPage(pageNum) {
        loading.textContent = 'Rendering page ' + pageNum + '…';
        loading.style.display = '';
        const page = await pdf.getPage(pageNum);
        let viewport = page.getViewport({ scale: currentScale });
        const canvas = document.createElement('canvas');
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise;
        scroller.innerHTML = '';
        scroller.appendChild(canvas);
        scroller.scrollTop = 0;
        currentPage = pageNum;
        toolbar.querySelector('.pdf-cur').textContent = pageNum;
        toolbar.querySelector('.pdf-zoom-level').textContent = Math.round(currentScale * 100) + '%';
        loading.style.display = 'none';
      }

      document.getElementById('pdfPrev').addEventListener('click', () => { if (currentPage > 1) renderPage(currentPage - 1); });
      document.getElementById('pdfNext').addEventListener('click', () => { if (currentPage < numPages) renderPage(currentPage + 1); });
      document.getElementById('pdfIn').addEventListener('click', () => { currentScale = Math.min(3, currentScale + 0.25); renderPage(currentPage); });
      document.getElementById('pdfOut').addEventListener('click', () => { currentScale = Math.max(0.5, currentScale - 0.25); renderPage(currentPage); });

      // Keyboard nav
      container.tabIndex = 0;
      container.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft' && currentPage > 1) renderPage(currentPage - 1);
        if (e.key === 'ArrowRight' && currentPage < numPages) renderPage(currentPage + 1);
      });

      // Multi-page mode (>5 pages) — render all with virtualization hint
      if (numPages <= 8) {
        // Render all at once for small docs
        for (let i = 1; i <= numPages; i++) {
          const page = await pdf.getPage(i);
          let viewport = page.getViewport({ scale: currentScale });
          const canvas = document.createElement('canvas');
          canvas.width = viewport.width;
          canvas.height = viewport.height;
          canvas.className = 'pdf-page-canvas';
          await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise;
          scroller.appendChild(canvas);
        }
        loading.style.display = 'none';
        toolbar.querySelector('.pdf-cur').textContent = numPages;
        // Hide nav for multi-page
        document.getElementById('pdfPrev').style.display = 'none';
        document.getElementById('pdfNext').style.display = 'none';
      } else {
        await renderPage(1);
      }
    } catch (e) {
      container.innerHTML =
        '<div class="doc-error">⚠ PDF render failed:<br>' + e.message + '</div>';
    }
  }

  // ── DOCX Renderer ──────────────────────────────────────
  async function renderDOCX(absPath, container) {
    await loadVendor('mammoth', '/vendor/mammoth/mammoth.browser.min.js');
    container.innerHTML = '<div class="doc-loading">Parsing document…</div>';

    try {
      const resp = await fetch('/api/content/download?path=' + encodeURIComponent(absPath));
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const arrayBuf = await resp.arrayBuffer();

      const result = await window.mammoth.convertToHtml(
        { arrayBuffer: arrayBuf },
        {
          styleMap: [
            "p[style-name='Heading 1'] => h1:fresh",
            "p[style-name='Heading 2'] => h2:fresh",
            "p[style-name='Heading 3'] => h3:fresh",
            "p[style-name='Title'] => h1.title:fresh",
            "p[style-name='Subtitle'] => h2.subtitle:fresh",
            "b => strong",
            "i => em",
            "u => u",
          ],
          convertImage: window.mammoth.images.imgElement(function (image) {
            return image.read('base64').then(function (imageBuffer) {
              return { src: 'data:' + image.contentType + ';base64,' + imageBuffer };
            });
          }),
        }
      );

      // Extract document title from first heading or filename
      const titleMatch = result.value.match(/<h[1-3][^>]*>(.*?)<\/h[1-3]>/i);
      const docTitle = titleMatch ? titleMatch[1].replace(/<[^>]+>/g, '') : '';

      // Build a document-style page view
      let metaHtml = '';
      if (docTitle) {
        metaHtml = '<div class="docx-meta"><div class="docx-title">' + docTitle + '</div>'
          + '<div class="docx-source">' + absPath.split('/').pop() + '</div></div>';
      }

      container.innerHTML =
        '<div class="doc-viewer">' +
        '<div class="docx-page">' +
        metaHtml +
        '<div class="docx-rendered">' + result.value + '</div>' +
        '</div></div>';

      // Handle mammoth messages (warnings about unsupported elements)
      if (result.messages && result.messages.length > 0) {
        const warnDiv = document.createElement('div');
        warnDiv.className = 'docx-warnings';
        warnDiv.innerHTML = '⚠ ' + result.messages.length + ' conversion note(s)';
        container.querySelector('.docx-page').appendChild(warnDiv);
      }
    } catch (e) {
      container.innerHTML =
        '<div class="doc-error">⚠ DOCX parse failed:<br>' + e.message + '</div>';
    }
  }

  // ── XLSX Renderer ──────────────────────────────────────
  async function renderXLSX(data, container) {
    await loadVendor('XLSX', '/vendor/xlsx/dist/xlsx.full.min.js');
    try {
      const book = window.XLSX.read(data, { type: 'array' });
      _xlsxBook = book;

      container.innerHTML = '<div class="doc-loading">Building spreadsheet view…</div>';

      const sheetNames = book.SheetNames;

      // Sheet tabs
      let tabHtml = '<div class="xlsx-tabs">';
      sheetNames.forEach((name, i) => {
        tabHtml += '<button class="xlsx-tab' + (i === 0 ? ' active' : '') + '" data-sheet="' + i + '">' + name + '</button>';
      });
      tabHtml += '</div>';

      const wrapper = document.createElement('div');
      wrapper.className = 'xlsx-wrapper';
      wrapper.innerHTML = tabHtml + '<div class="xlsx-area"></div>';
      container.innerHTML = '';
      container.appendChild(wrapper);

      function colLetter(n) {
        let s = '';
        while (n >= 0) { s = String.fromCharCode(65 + (n % 26)) + s; n = Math.floor(n / 26) - 1; }
        return s;
      }

      function showSheet(idx) {
        const sn = sheetNames[idx];
        const ws = book.Sheets[sn];
        const range = window.XLSX.utils.decode_range(ws['!ref'] || 'A1');
        const totalRows = range.e.r + 1;
        const totalCols = range.e.c + 1;

        // Get column widths from sheet
        const colWidths = (ws['!cols'] || []).map(c => c?.wch || 12);

        // Build a proper spreadsheet grid
        let html = '<table class="xlsx-grid" style="--total-cols:' + totalCols + '">';

        // Column header row
        html += '<thead><tr><th class="xlsx-corner">#</th>';
        for (let c = 0; c < totalCols; c++) {
          const w = colWidths[c] || 12;
          html += '<th class="xlsx-col-header" style="min-width:' + (w * 8) + 'px">' + colLetter(c) + '</th>';
        }
        html += '</tr></thead><tbody>';

        // Data rows
        for (let r = 0; r < totalRows; r++) {
          html += '<tr>';
          html += '<td class="xlsx-row-header">' + (r + 1) + '</td>';
          for (let c = 0; c < totalCols; c++) {
            const addr = window.XLSX.utils.encode_cell({ r, c });
            const cell = ws[addr];
            let val = '';
            let cls = 'xlsx-cell';
            if (cell) {
              if (cell.t === 'n') { cls += ' xlsx-num'; val = cell.w !== undefined ? cell.w : cell.v; }
              else if (cell.t === 'b') { cls += ' xlsx-bool'; val = cell.v ? 'TRUE' : 'FALSE'; }
              else if (cell.t === 'd') { cls += ' xlsx-date'; val = cell.w || cell.v; }
              else if (cell.t === 'e') { cls += ' xlsx-error'; val = '#ERR'; }
              else { cls += ' xlsx-text'; val = cell.w !== undefined ? cell.w : (cell.v || ''); }
            }
            html += '<td class="' + cls + '">' + (val !== '' ? escapeHtml(String(val)) : '') + '</td>';
          }
          html += '</tr>';
        }
        html += '</tbody></table>';

        wrapper.querySelector('.xlsx-area').innerHTML = html;
        wrapper.querySelectorAll('.xlsx-tab').forEach((btn, bi) => {
          btn.classList.toggle('active', bi === idx);
        });
      }

      wrapper.querySelectorAll('.xlsx-tab').forEach(btn => {
        btn.addEventListener('click', () => {
          showSheet(parseInt(btn.dataset.sheet));
        });
      });

      showSheet(0);
    } catch (e) {
      container.innerHTML =
        '<div class="doc-error">⚠ XLSX parse failed:<br>' + e.message + '</div>';
    }
  }

  // ── Image Renderer ─────────────────────────────────────
  function renderImage(absPath, fileData, container) {
    container.innerHTML =
      '<div class="doc-loading">Loading image…</div>';

    const loadingEl = container.querySelector('.doc-loading');

    // Try to fetch the raw file so we can show it via blob URL
    fetch('/api/content/download?path=' + encodeURIComponent(absPath))
      .then(r => r.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const img = new Image();
        img.onload = () => {
          container.innerHTML =
            '<div class="doc-viewer image-viewer">' +
              '<div class="img-toolbar">' +
                '<button class="preview-btn" id="imgFit">Fit</button>' +
                '<button class="preview-btn" id="imgActual">1:1</button>' +
                '<span class="img-dims">' + img.naturalWidth + ' × ' + img.naturalHeight + ' px</span>' +
              '</div>' +
              '<div class="img-scroller"><img src="' + url + '" /></div>' +
            '</div>';
          const scroller = container.querySelector('.img-scroller');
          const image = container.querySelector('img');
          container.querySelector('#imgFit').addEventListener('click', () => {
            image.style.maxWidth = '100%';
            image.style.height = 'auto';
          });
          container.querySelector('#imgActual').addEventListener('click', () => {
            image.style.maxWidth = 'none';
            image.style.height = 'auto';
          });
          // Zoom with wheel
          scroller.addEventListener('wheel', e => {
            if (e.ctrlKey || e.metaKey) {
              e.preventDefault();
              const delta = e.deltaY > 0 ? -0.1 : 0.1;
              const scale = Math.max(0.1, Math.min(5, (parseFloat(image.dataset.scale) || 1) + delta));
              image.dataset.scale = scale;
              image.style.maxWidth = (scale * 100) + '%';
              image.style.height = 'auto';
            }
          });
        };
        img.onerror = () => {
          container.innerHTML = '<div class="doc-error">⚠ Failed to load image</div>';
        };
        img.src = url;
      })
      .catch(e => {
        container.innerHTML = '<div class="doc-error">⚠ Image load failed:<br>' + e.message + '</div>';
      });
  }

  // ── HTML Preview (iframe) ──────────────────────────────
  function renderHTML(absPath, data, container) {
    const htmlContent = typeof data === 'string' ? data : data.content || '';
    if (!htmlContent) {
      container.innerHTML = '<div class="preview-empty"><div>Empty file</div></div>';
      return;
    }
    // Sanitize — only allow safe tags
    const allowed = new Set(['div','span','p','br','h1','h2','h3','h4','h5','h6','table','thead','tbody','tr','th','td',
      'ul','ol','li','a','b','i','u','em','strong','img','form','input','button','select','option',
      'textarea','label','fieldset','legend','section','article','header','footer','nav','main',
      'style']);
    const clean = htmlContent
      .replace(/<script[\s\S]*?<\/script>/gi, '')
      .replace(/<iframe[^>]*>/gi, '')
      .replace(/ on\w+="[^"]*"/gi, '');

    container.innerHTML =
      '<div class="html-preview-wrapper">' +
        '<div class="preview-html-frame" style="width:100%;height:60vh;border:none;"></div>' +
      '</div>';

    setTimeout(() => {
      const iframe = container.querySelector('iframe');
      const doc = iframe.contentDocument || iframe.contentWindow.document;
      doc.open();
      doc.write(clean);
      doc.close();
    }, 100);
  }

  // ── Code / JSON with syntax highlighting ───────────────
  function highlightCode(code, lang) {
    // Use highlight.js if available
    if (window.hljs && lang) {
      try { return window.hljs.highlight(code, { language: lang, ignoreIllegals: true }).value; } catch(e) {}
    }
    // Escape HTML first
    let html = code.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    // Built-in lightweight tokenizer — single pass
    const keywords = {
      python: ['def','class','import','from','return','if','elif','else','for','while','try','except','finally','with','as','in','not','and','or','is','None','True','False','yield','lambda','pass','break','continue','raise','global','nonlocal','assert','del','print'],
      javascript: ['function','const','let','var','return','if','else','for','while','do','switch','case','break','continue','try','catch','finally','throw','new','this','class','extends','super','import','export','default','async','await','true','false','null','undefined','typeof','instanceof','of','in','delete'],
      typescript: ['function','const','let','var','return','if','else','for','while','do','switch','case','break','continue','try','catch','finally','throw','new','this','class','extends','super','import','export','default','async','await','true','false','null','undefined','interface','type','enum','implements','private','protected','public','readonly'],
      bash: ['if','then','else','elif','fi','for','while','do','done','case','esac','function','return','echo','exit','set','unset','export','source','alias'],
      sh: ['if','then','else','elif','fi','for','while','do','done','case','esac','function','return','echo','exit','set','unset','export','source','alias'],
    };
    const kwList = keywords[lang] || [];
    // Tokenize: split into tokens (strings, comments, keywords, plain)
    const tokens = [];
    let i = 0;
    while (i < html.length) {
      // Check for comment
      if (lang === 'python' && html[i] === '#') {
        let end = html.indexOf('\n', i);
        if (end === -1) end = html.length;
        tokens.push({type:'comment', text: html.slice(i, end)});
        i = end;
        continue;
      }
      if ((lang === 'javascript' || lang === 'typescript') && html[i] === '/' && html[i+1] === '/') {
        let end = html.indexOf('\n', i);
        if (end === -1) end = html.length;
        tokens.push({type:'comment', text: html.slice(i, end)});
        i = end;
        continue;
      }
      // Check for string
      if (html[i] === '"' || html[i] === "'") {
        const quote = html[i];
        let j = i + 1;
        while (j < html.length && html[j] !== quote) {
          if (html[j] === '\\') j++; // skip escaped
          j++;
        }
        if (j < html.length) j++; // include closing quote
        tokens.push({type:'string', text: html.slice(i, j)});
        i = j;
        continue;
      }
      // Check for number
      if (/\d/.test(html[i]) && (i === 0 || !/\w/.test(html[i-1]))) {
        let j = i;
        while (j < html.length && /[\d.]/.test(html[j])) j++;
        tokens.push({type:'number', text: html.slice(i, j)});
        i = j;
        continue;
      }
      // Check for keyword
      if (/[a-zA-Z_]/.test(html[i])) {
        let j = i;
        while (j < html.length && /[\w]/.test(html[j])) j++;
        const word = html.slice(i, j);
        if (kwList.includes(word)) {
          tokens.push({type:'keyword', text: word});
        } else if (j < html.length && html[j] === '(') {
          tokens.push({type:'function', text: word});
        } else {
          tokens.push({type:'plain', text: word});
        }
        i = j;
        continue;
      }
      // Plain character
      tokens.push({type:'plain', text: html[i]});
      i++;
    }
    // Build output
    return tokens.map(t => {
      if (t.type === 'comment') return '<span class="hljs-comment">' + t.text + '</span>';
      if (t.type === 'string') return '<span class="hljs-string">' + t.text + '</span>';
      if (t.type === 'number') return '<span class="hljs-number">' + t.text + '</span>';
      if (t.type === 'keyword') return '<span class="hljs-keyword">' + t.text + '</span>';
      if (t.type === 'function') return '<span class="hljs-function">' + t.text + '</span>';
      return t.text;
    }).join('');
  }

  function renderCodeOrText(content, ext, container) {
    const langMap = {
      '.py': 'python', '.js': 'javascript', '.ts': 'typescript', '.jsx': 'jsx',
      '.tsx': 'tsx', '.sh': 'bash', '.bash': 'bash', '.css': 'css', '.html': 'xml',
      '.xml': 'xml', '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
      '.sql': 'sql', '.rs': 'rust', '.go': 'go', '.rb': 'ruby', '.php': 'php',
      '.java': 'java', '.c': 'c', '.cpp': 'cpp', '.cs': 'csharp',
      '.swift': 'swift', '.kt': 'kotlin', '.md': 'markdown', '.toml': 'toml',
    };
    const lang = langMap[ext] || '';
    const highlighted = highlightCode(content, lang);
    const lines = content.split('\n');
    const lineNums = lines.map((_, i) => '<span class="code-line-num">' + (i + 1) + '</span>').join('');

    container.innerHTML =
      '<div class="code-preview-wrapper">' +
        '<div class="code-preview-bar">' +
          '<span class="code-lang-badge">' + (lang || 'text') + '</span>' +
          '<span class="code-lines-count">' + lines.length + ' lines</span>' +
          '<button class="preview-btn code-copy-btn" style="margin-left:auto;padding:2px 8px;font-size:10px">Copy</button>' +
        '</div>' +
        '<div class="code-preview-container">' +
          '<div class="code-line-numbers">' + lineNums + '</div>' +
          '<pre class="code-content"><code>' + highlighted + '</code></pre>' +
        '</div>' +
      '</div>';

    container.querySelector('.code-copy-btn').addEventListener('click', () => {
      navigator.clipboard.writeText(content).then(() => {
        const btn = container.querySelector('.code-copy-btn');
        btn.textContent = '✓';
        setTimeout(() => btn.textContent = 'Copy', 1500);
      });
    });
  }

  // ── Markdown Renderer ──────────────────────────────────
  function renderMarkdown(content, container) {
    let html = content;
    if (window.marked) {
      try { html = window.marked.parse(content); } catch(e) { html = escapeHtml(content); }
    } else {
      // Minimal markdown fallback: headers, bold, italic, lists, code
      html = escapeHtml(content);
      html = html.replace(/^### (.+)/gm, '<h3>$1</h3>');
      html = html.replace(/^## (.+)/gm, '<h2>$1</h2>');
      html = html.replace(/^# (.+)/gm, '<h1>$1</h1>');
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
      html = html.replace(/^[-*] (.+)/gm, '<li>$1</li>');
      html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1></code></pre>');
      html = html.replace(/`(.+?)`/g, '<code>$1</code>');
      html = html.replace(/\n\n/g, '</p><p>');
      html = '<p>' + html + '</p>';
    }
    container.innerHTML = '<div class="preview-md">' + html + '</div>';
  }

  // ── Main dispatcher ────────────────────────────────────
  async function renderFile(absPath, fileData, container) {
    const ext = (absPath.match(/\.[a-zA-Z0-9]+$/) || [''])[0].toLowerCase();

    await ensureAllVendors();

    if (['.jpg','.jpeg','.png','.gif','.webp','.svg'].includes(ext)) {
      renderImage(absPath, fileData, container);
    } else if (ext === '.pdf') {
      await renderPDF(absPath, container);
    } else if (ext === '.docx' || ext === '.doc') {
      await renderDOCX(absPath, container);
    } else if (ext === '.xlsx' || ext === '.xls' || ext === '.csv') {
      try {
        const resp = await fetch('/api/content/download?path=' + encodeURIComponent(absPath));
        const buf = await resp.arrayBuffer();
        renderXLSX(buf, container);
      } catch(e) {
        container.innerHTML = '<div class="doc-error">⚠ ' + e.message + '</div>';
      }
    } else if (ext === '.html' || ext === '.htm') {
      renderHTML(absPath, fileData, container);
    } else if (ext === '.md') {
      const text = fileData && fileData.content ? fileData.content : '';
      renderMarkdown(text, container);
    } else if (['.py','.js','.ts','.jsx','.tsx','.sh','.bash','.css','.xml','.json',
      '.yaml','.yml','.sql','.env','.conf','.cfg','.ini','.toml','.rs','.go',
      '.rb','.php','.java','.c','.cpp','.cs','.swift','.kt','.lua','.pl','.ex'].includes(ext)) {
      const text = fileData && fileData.content ? fileData.content : '';
      renderCodeOrText(text, ext, container);
    } else {
      const text = fileData && fileData.content ? fileData.content : '';
      if (text && text.length > 0) {
        container.innerHTML = '<div class="preview-text">' + escapeHtml(text) + '</div>';
      } else {
        container.innerHTML =
          '<div class="preview-empty">' +
            '<div class="preview-empty-icon">📄</div>' +
            '<div>Preview not supported for ' + (ext || 'unknown') + ' files</div>' +
            '<div style="margin-top:8px;font-size:var(--font-size-xs);">Use Download to open</div>' +
          '</div>';
      }
    }
  }

  function escapeHtml(s) {
    if (!s) return '';
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // ── Export globally ────────────────────────────────────
  window.ContentViewer = {
    render: renderFile,
    isSupported: function(ext) {
      const s = ['.pdf','.docx','.doc','.xlsx','.xls','.csv','.html','.htm',
        '.jpg','.jpeg','.png','.gif','.webp','.svg','.py','.js','.ts','.sh',
        '.json','.yaml','.yml','.css','.md'];
      return s.includes(ext ? ext.toLowerCase() : '');
    }
  };

  // ── Init vendor loading early ──────────────────────────
  ensureAllVendors();
})();
