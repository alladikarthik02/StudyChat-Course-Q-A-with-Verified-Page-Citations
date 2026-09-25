import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App() {
  const [status, setStatus] = useState('Checking connection…');
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/ready', { signal: controller.signal })
      .then(response => setStatus(response.ok ? 'Database connected' : 'Database unavailable'))
      .catch(error => { if (error.name !== 'AbortError') setStatus('Backend unavailable'); });
    return () => controller.abort();
  }, []);
  return <main><p className="eyebrow">YOUR COURSE, WITH CONTEXT</p><h1>StudyChat</h1>
    <p>Answers you can trace back to the page.</p>
    <section aria-label="Project status"><span className="badge">Offline fixture mode</span>
      <h2>Your study space is taking shape.</h2>
      <p>PDF uploads and verified citations are being built in the next checkpoints.</p>
      <p role="status">{status}</p>
      <small>Fixture mode makes no API calls. It does not measure answer quality.</small>
    </section></main>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
