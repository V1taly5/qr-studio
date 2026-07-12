(function () {
    const state = { type: 'url', format: 'png' };

    const html = document.documentElement;
    const saved = localStorage.getItem('theme') || 'dark';
    html.setAttribute('data-theme', saved);

    document.getElementById('theme-toggle').addEventListener('click', () => {
        const cur = html.getAttribute('data-theme');
        const next = cur === 'light' ? 'dark' : 'light';
        html.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
    });

    function validate() {
        const generate = document.getElementById('generate');
        let data;
        let valid = true;

        if (state.type === 'url') {
            const input = document.getElementById('url-input');
            data = input.value.trim();
            valid = input.checkValidity() && data.length > 0;
        } else {
            const input = document.getElementById('text-input');
            data = input.value.trim();
            valid = data.length > 0;
        }

        generate.disabled = !valid;
        return valid;
    }

    function getData() {
        if (state.type === 'url') {
            return document.getElementById('url-input').value.trim();
        }
        return document.getElementById('text-input').value.trim();
    }

    document.querySelectorAll('[data-type]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('[data-type]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.type = btn.dataset.type;
            document.getElementById('url-group').classList.toggle('hidden', state.type !== 'url');
            document.getElementById('text-group').classList.toggle('hidden', state.type !== 'text');
            validate();
        });
    });

    document.querySelectorAll('[data-fmt]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('[data-fmt]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.format = btn.dataset.fmt;
        });
    });

    document.getElementById('url-input').addEventListener('input', validate);
    document.getElementById('text-input').addEventListener('input', validate);

    document.getElementById('generate').addEventListener('click', async () => {
        if (!validate()) return;

        const err = document.getElementById('error');
        const preview = document.getElementById('preview');
        err.classList.add('hidden');

        const data = getData();

        try {
            const res = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: state.type, data, format: state.format })
            });
            const json = await res.json();
            if (!json.success) throw new Error(json.detail || 'Failed');

            const container = document.getElementById('qr-container');
            container.innerHTML = '';
            if (state.format === 'svg') {
                container.innerHTML = json.data;
                const svg = container.querySelector('svg');
                if (svg) {
                    svg.setAttribute('width', '256');
                    svg.setAttribute('height', '256');
                }
            } else {
                const img = document.createElement('img');
                img.src = json.data;
                img.alt = 'QR Code';
                container.appendChild(img);
            }
            preview.classList.remove('hidden');

            document.getElementById('download').onclick = () => {
                const a = document.createElement('a');
                let objectUrl;
                if (state.format === 'svg') {
                    const blob = new Blob([json.data], {type: 'image/svg+xml'});
                    objectUrl = URL.createObjectURL(blob);
                    a.href = objectUrl;
                    a.download = 'qr-code.svg';
                } else {
                    a.href = json.data;
                    a.download = 'qr-code.png';
                }
                a.click();
                if (objectUrl) {
                    URL.revokeObjectURL(objectUrl);
                }
            };
        } catch (e) {
            err.textContent = e.message;
            err.classList.remove('hidden');
            preview.classList.add('hidden');
        }
    });

    validate();
})();
