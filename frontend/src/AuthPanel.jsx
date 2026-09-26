import { useState } from 'react'
import { createUserWithEmailAndPassword, signInWithEmailAndPassword } from 'firebase/auth'
import { auth } from './firebase'

function readableAuthError(error) {
  switch (error.code) {
    case 'auth/email-already-in-use':
      return 'That email already has an account. Try signing in instead.'
    case 'auth/invalid-credential':
    case 'auth/user-not-found':
    case 'auth/wrong-password':
      return 'The email or password was not recognized. Check them and try again.'
    case 'auth/weak-password':
      return 'Choose a password with at least 6 characters.'
    case 'auth/invalid-email':
      return 'Enter a valid email address.'
    case 'auth/operation-not-allowed':
      return 'Email and password sign-in is not enabled yet in Firebase Authentication.'
    default:
      return 'We could not complete that request. Please try again.'
  }
}

export default function AuthPanel() {
  const [mode, setMode] = useState('signup')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    setErrorMessage('')

    try {
      if (mode === 'signup') {
        await createUserWithEmailAndPassword(auth, email.trim(), password)
      } else {
        await signInWithEmailAndPassword(auth, email.trim(), password)
      }
    } catch (error) {
      setErrorMessage(readableAuthError(error))
    } finally {
      setBusy(false)
    }
  }

  function changeMode(nextMode) {
    setMode(nextMode)
    setErrorMessage('')
  }

  const isSignUp = mode === 'signup'

  return (
    <div className="auth-shell">
      <header className="topbar auth-topbar">
        <a className="brand" href="#top" aria-label="Nourish home">
          <span className="brand-mark">n</span>
          <span>nourish<span className="brand-dot">.</span></span>
        </a>
        <div className="topbar-note"><span className="status-dot" /> Personal planning, one step at a time</div>
      </header>

      <main className="auth-main" id="top">
        <section className="auth-story">
          <p className="eyebrow">A LITTLE MORE YOU, A LITTLE LESS GUESSWORK</p>
          <h1>Make room for<br /><em>better days.</em></h1>
          <p>Sign in to begin shaping meal ideas around your routine, preferences, and goals.</p>
          <div className="auth-promise"><span aria-hidden="true">✳</span><span>Use fictional profile details for this student demo. The app is educational, not medical advice.</span></div>
        </section>

        <section className="auth-card" aria-labelledby="auth-title">
          <div className="auth-tabs" role="tablist" aria-label="Account access">
            <button type="button" role="tab" aria-selected={isSignUp} className={isSignUp ? 'active' : ''} onClick={() => changeMode('signup')}>Create account</button>
            <button type="button" role="tab" aria-selected={!isSignUp} className={!isSignUp ? 'active' : ''} onClick={() => changeMode('signin')}>Sign in</button>
          </div>
          <p className="eyebrow">{isSignUp ? 'START YOUR JOURNEY' : 'WELCOME BACK'}</p>
          <h2 id="auth-title">{isSignUp ? 'Create your account' : 'Sign in to Nourish'}</h2>
          <p className="auth-subtitle">{isSignUp ? 'Use a dedicated demo email for this project.' : 'Enter the email and password for your account.'}</p>

          <form className="auth-form" onSubmit={handleSubmit}>
            <label>Email address<input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" required /></label>
            <label>Password<input type="password" autoComplete={isSignUp ? 'new-password' : 'current-password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 6 characters" minLength="6" required /></label>
            {errorMessage && <p className="auth-error" role="alert">{errorMessage}</p>}
            <button className="auth-submit" type="submit" disabled={busy}>{busy ? 'Please wait…' : isSignUp ? 'Create account' : 'Sign in'}<span aria-hidden="true">→</span></button>
          </form>
          <p className="auth-footnote">Your Firebase account is used to protect access. Profile saving is the next step.</p>
        </section>
      </main>
      <footer className="footer"><span>nourish<span className="brand-dot">.</span></span><span>Small steps, made personal.</span></footer>
    </div>
  )
}
