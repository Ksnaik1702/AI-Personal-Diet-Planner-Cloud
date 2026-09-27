import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { onAuthStateChanged, signOut } from 'firebase/auth'
import { collection, doc, getDoc, getDocs, limit, orderBy, query, serverTimestamp, setDoc } from 'firebase/firestore'
import { auth, db } from './firebase'
import AuthPanel from './AuthPanel'
import { downloadPlanFile, hasPlanFile, savePlanFile } from './localObjectStorage'
import './style.css'

const initialProfile = {
  age: '',
  sex: '',
  heightCm: '',
  weightKg: '',
  activity: '',
  goal: '',
  diet: '',
  allergies: '',
  budget: '',
  cuisine: '',
  timeline: '',
}

function PlannerForm({ user, onSignOut }) {
  const [screen, setScreen] = useState(window.location.pathname === '/plans' ? 'plans' : 'profile')
  const [profile, setProfile] = useState(initialProfile)
  const [profileSaved, setProfileSaved] = useState(false)
  const [submissionState, setSubmissionState] = useState('idle')
  const [submissionMessage, setSubmissionMessage] = useState('')
  const [profileLoadState, setProfileLoadState] = useState('loading')
  const [planState, setPlanState] = useState('idle')
  const [planMessage, setPlanMessage] = useState('')
  const [generatedPlan, setGeneratedPlan] = useState(null)
  const [planHistory, setPlanHistory] = useState([])
  const [localPlanFileReady, setLocalPlanFileReady] = useState(false)
  const allergyEntry = String(profile.allergies).trim().toLowerCase()
  const hasAllergyAvoidance = allergyEntry !== '' && !['none', 'no', 'no allergies', 'nil', 'n/a', 'na'].includes(allergyEntry)

  useEffect(() => {
    const handleHistoryChange = () => setScreen(window.location.pathname === '/plans' ? 'plans' : 'profile')
    window.addEventListener('popstate', handleHistoryChange)
    return () => window.removeEventListener('popstate', handleHistoryChange)
  }, [])

  function navigateTo(nextScreen) {
    const nextPath = nextScreen === 'plans' ? '/plans' : '/'
    if (window.location.pathname !== nextPath) window.history.pushState({}, '', nextPath)
    setScreen(nextScreen)
    window.scrollTo({ top: 0, behavior: 'auto' })
  }

  useEffect(() => {
    let active = true

    async function loadSavedProfile() {
      try {
        const profileRef = doc(db, 'users', user.uid, 'profiles', 'current')
        const snapshot = await getDoc(profileRef)
        if (!active) return

        if (snapshot.exists()) {
          const savedProfile = snapshot.data()
          setProfile(Object.fromEntries(
            Object.entries(initialProfile).map(([key, emptyValue]) => [key, savedProfile[key] ?? emptyValue]),
          ))
          setProfileSaved(true)
        }
      } catch {
        if (active) {
          setSubmissionState('error')
          setSubmissionMessage('Could not load your saved profile from Firestore. Check the connection and rules.')
        }
      } finally {
        if (active) setProfileLoadState('loaded')
      }
    }

    loadSavedProfile()
    return () => { active = false }
  }, [user.uid])

  useEffect(() => {
    let active = true

    async function loadLatestPlan() {
      try {
        const plansRef = collection(db, 'users', user.uid, 'plans')
        const latestPlanQuery = query(plansRef, orderBy('savedAt', 'desc'), limit(10))
        const snapshot = await getDocs(latestPlanQuery)
        if (!active || snapshot.empty) return

        const savedPlans = snapshot.docs.map((planDoc) => planDoc.data())
        const savedPlan = savedPlans[0]
        setPlanHistory(savedPlans)
        setGeneratedPlan(savedPlan)
        setPlanState('saved')
        setPlanMessage('Your latest meal plan was loaded from your private Firestore account.')
        setLocalPlanFileReady(await hasPlanFile(user.uid, savedPlan.planId))
      } catch {
        if (active) {
          setPlanState('error')
          setPlanMessage('Could not load your saved plan. Check your connection and Firestore rules.')
        }
      }
    }

    loadLatestPlan()
    return () => { active = false }
  }, [user.uid])

  function updateField(event) {
    setProfile({ ...profile, [event.target.name]: event.target.value })
    setProfileSaved(false)
    setSubmissionState('idle')
    setSubmissionMessage('')
    setPlanState('idle')
    setPlanMessage('')
    setGeneratedPlan(null)
    setLocalPlanFileReady(false)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmissionState('submitting')
    setSubmissionMessage('')

    const profileForApi = {
      ...profile,
      age: Number(profile.age),
      heightCm: Number(profile.heightCm),
      weightKg: Number(profile.weightKg),
    }

    try {
      await setDoc(
        doc(db, 'users', user.uid, 'profiles', 'current'),
        { ...profileForApi, updatedAt: serverTimestamp() },
        { merge: true },
      )

      setProfileSaved(true)
      setSubmissionState('success')
      setSubmissionMessage('Your profile was saved to your private Firestore account.')
    } catch (error) {
      setSubmissionState('error')
      setSubmissionMessage(
        error.code === 'permission-denied'
          ? 'Firestore blocked this save. Publish the user-specific rules from firestore.rules, then try again.'
          : error.code === 'unavailable'
            ? 'Could not reach Firestore. Check your internet connection and try again.'
            : 'Could not save the profile. Please check the Firebase setup and try again.',
      )
    }
  }

  async function handleGeneratePlan() {
    setPlanState('generating')
    setPlanMessage('')
    setGeneratedPlan(null)
    setLocalPlanFileReady(false)

    const profileForApi = {
      ...profile,
      age: Number(profile.age),
      heightCm: Number(profile.heightCm),
      weightKg: Number(profile.weightKg),
    }

    let savedToFirestore = false
    try {
      const response = await fetch('http://127.0.0.1:8000/plans/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileForApi),
      })
      const result = await response.json()
      if (!response.ok) {
        const message = typeof result.detail === 'string'
          ? result.detail
          : result.detail?.[0]?.msg ?? 'Please review the profile details and try again.'
        throw new Error(message)
      }

      setGeneratedPlan(result)
      await setDoc(
        doc(db, 'users', user.uid, 'plans', result.planId),
        { ...result, savedAt: serverTimestamp() },
      )
      savedToFirestore = true
      setPlanHistory((plans) => [result, ...plans.filter((plan) => plan.planId !== result.planId)].slice(0, 10))
      await savePlanFile(user.uid, result)
      setLocalPlanFileReady(true)
      setPlanState('saved')
      setPlanMessage('Your meal plan was saved to Firestore and a local browser copy.')
      navigateTo('plans')
    } catch (error) {
      if (savedToFirestore) {
        setPlanState('saved')
        setPlanMessage('Your meal plan was saved to Firestore, but its local browser copy could not be created.')
        navigateTo('plans')
      } else if (error.message.startsWith('The meal planner')) {
        setPlanState('error')
        setPlanMessage(error.message)
      } else if (error.code === 'permission-denied') {
        setPlanState('error')
        setPlanMessage('The plan was generated, but Firestore blocked saving it. Check the plans rule in firestore.rules.')
      } else if (error instanceof TypeError) {
        setPlanState('error')
        setPlanMessage('Could not reach the planner API. Make sure the FastAPI server is running, then try again.')
      } else {
        setPlanState('error')
        setPlanMessage(error.message || 'Could not generate or save the plan. Please try again.')
      }
    }
  }

  async function handlePlanSelection(event) {
    const selectedPlan = planHistory.find((plan) => plan.planId === event.target.value)
    if (!selectedPlan) return

    setGeneratedPlan(selectedPlan)
    setPlanState('saved')
    setPlanMessage('Showing a plan saved to your private Firestore account.')
    try {
      setLocalPlanFileReady(await hasPlanFile(user.uid, selectedPlan.planId))
    } catch {
      setLocalPlanFileReady(false)
    }
  }

  async function handleDownloadPlan() {
    if (!generatedPlan) return
    try {
      await downloadPlanFile(user.uid, generatedPlan.planId)
    } catch {
      setPlanState('error')
      setPlanMessage('The local plan file is not available. Generate the plan again to create it.')
    }
  }

  if (profileLoadState === 'loading') {
    return <main className="auth-loading" aria-live="polite">Loading your saved profile…</main>
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" onClick={(event) => { event.preventDefault(); navigateTo('profile') }} aria-label="Nourish home">
          <span className="brand-mark">n</span>
          <span>nourish<span className="brand-dot">.</span></span>
        </a>
        <div className="topbar-account"><span className="topbar-note"><span className="status-dot" /> {user.email}</span><button className="signout-button" type="button" onClick={onSignOut}>Sign out</button></div>
      </header>

      <main className={`page ${screen === 'plans' ? 'page-plans' : ''}`} id="top">
        {screen === 'profile' && <section className="intro">
          <p className="eyebrow">YOUR PERSONAL FOOD COMPASS</p>
          <h1>A plan that starts<br />with <em>you.</em></h1>
          <p className="intro-copy">Tell us a little about your routine and preferences. We’ll use these details to shape meal ideas around your everyday life.</p>
          <div className="step-card">
            <div className="step-number">01</div>
            <div><strong>Your profile</strong><span>About 2 minutes</span></div>
            <div className="step-line" />
            <div className="step-muted">02<br /><span>Your plan</span></div>
          </div>
          <div className="privacy-note"><span aria-hidden="true">✳</span><p><strong>Your information stays yours.</strong><br />Your profile is stored in a Firestore record under your signed-in account.</p></div>
        </section>}

        <section className="form-card" aria-labelledby="form-title">
          {screen === 'profile' && <>
          <div className="form-heading">
            <div>
              <p className="eyebrow">LET’S GET TO KNOW YOU</p>
              <h2 id="form-title">Your profile</h2>
            </div>
            <span className="required-note">* Required</span>
          </div>

          <form onSubmit={handleSubmit}>
            <fieldset>
              <legend>About you</legend>
              <div className="field-grid three-col">
                <label>Age <span>*</span><input name="age" type="number" min="13" max="120" placeholder="e.g. 24" value={profile.age} onChange={updateField} required /></label>
                <label>Sex for nutrition estimate <span>*</span><select name="sex" value={profile.sex} onChange={updateField} required><option value="">Choose one</option><option value="female">Female</option><option value="male">Male</option><option value="other">Other / prefer not to say</option></select></label>
                <label>Activity level <span>*</span><select name="activity" value={profile.activity} onChange={updateField} required><option value="">Choose one</option><option value="low">Mostly sitting</option><option value="light">Lightly active</option><option value="moderate">Moderately active</option><option value="high">Very active</option></select></label>
                <label>Height (cm) <span>*</span><input name="heightCm" type="number" min="80" max="250" placeholder="e.g. 165" value={profile.heightCm} onChange={updateField} required /></label>
                <label>Weight (kg) <span>*</span><input name="weightKg" type="number" min="25" max="350" step="0.1" placeholder="e.g. 62" value={profile.weightKg} onChange={updateField} required /></label>
              </div>
            </fieldset>

            <fieldset>
              <legend>Your preferences</legend>
              <div className="field-grid two-col">
                <label>Your goal <span>*</span><select name="goal" value={profile.goal} onChange={updateField} required><option value="">Choose one</option><option value="balanced">Eat more balanced meals</option><option value="lose">Weight management — lose</option><option value="maintain">Weight management — maintain</option><option value="gain">Weight management — gain</option><option value="energy">Support my energy and routine</option></select></label>
                <label>Eating style <span>*</span><select name="diet" value={profile.diet} onChange={updateField} required><option value="">Choose one</option><option value="omnivore">No specific preference</option><option value="vegetarian">Vegetarian</option><option value="vegan">Vegan</option><option value="pescatarian">Pescatarian</option><option value="other">Other</option></select></label>
                <label>Food allergies or foods to avoid<input name="allergies" type="text" aria-describedby="allergy-help" placeholder="e.g. peanuts, shellfish" value={profile.allergies} onChange={updateField} /><small id="allergy-help">Separate multiple items with commas. Review all ingredients and food labels when checking your plan.</small></label>
                <label>Weekly food budget <span>*</span><input name="budget" type="text" placeholder="e.g. ₹2,000" value={profile.budget} onChange={updateField} required /></label>
                <label>Favourite cuisines<input name="cuisine" type="text" placeholder="e.g. Indian, Mediterranean" value={profile.cuisine} onChange={updateField} /></label>
                <label>Planning timeline <span>*</span><select name="timeline" value={profile.timeline} onChange={updateField} required><option value="">Choose one</option><option value="week">One week</option><option value="two-weeks">Two weeks</option><option value="month">One month</option></select></label>
              </div>
            </fieldset>

            <div className="form-footer">
              <p>Plans are for general educational use, not medical advice.</p>
              <button type="submit" disabled={submissionState === 'submitting'}>{submissionState === 'submitting' ? 'Sending…' : 'Save profile'} <span aria-hidden="true">→</span></button>
            </div>
            {submissionMessage && <p className={`submission-message ${submissionState}`} role={submissionState === 'error' ? 'alert' : 'status'}>{submissionMessage}</p>}
          </form>

          {profileSaved && <section className="plan-builder" aria-labelledby="plan-builder-title">
            {hasAllergyAvoidance && <p className="allergy-status" role="status">We’ll filter meals using their listed ingredients and allergen tags. Items not found in the available meal list will be flagged for review. Always check ingredients and food labels.</p>}
            <div className="plan-builder-heading">
              <div>
                <p className="eyebrow">YOUR NEXT STEP</p>
                <h3 id="plan-builder-title">Ready for meal ideas?</h3>
              </div>
              <div className="plan-builder-actions">
                {planHistory.length > 0 && <button type="button" className="view-plans-button" onClick={() => navigateTo('plans')}>View saved plans</button>}
                <button type="button" className="generate-button" onClick={handleGeneratePlan} disabled={planState === 'generating'}>
                  {planState === 'generating' ? 'Generating…' : 'Generate meal plan'} <span aria-hidden="true">→</span>
                </button>
              </div>
            </div>
            {planMessage && <p className={`submission-message ${planState === 'saved' ? 'success' : 'error'}`} role={planState === 'error' ? 'alert' : 'status'}>{planMessage}</p>}
          </section>}
          </>}

          {screen === 'plans' && <>
            <button type="button" className="back-to-profile" onClick={() => navigateTo('profile')}>← Back to profile</button>
            <div className="form-heading plan-page-title">
              <div><p className="eyebrow">YOUR SAVED IDEAS</p><h2 id="form-title">Your meal plan</h2></div>
            </div>
            {generatedPlan && planHistory.length > 1 && <label className="plan-history-picker">Saved plans
              <select value={generatedPlan.planId} onChange={handlePlanSelection}>
                {planHistory.map((plan, index) => {
                  const timestamp = plan.createdAt ? new Date(plan.createdAt) : plan.savedAt?.toDate?.()
                  const dateText = timestamp && !Number.isNaN(timestamp.getTime()) ? timestamp.toLocaleString() : 'date unavailable'
                  return <option value={plan.planId} key={plan.planId}>
                    {index === 0 ? 'Latest plan' : 'Earlier plan'} · {dateText} · {plan.planId.slice(0, 8)}
                  </option>
                })}
              </select>
            </label>}

          {generatedPlan ? <section className="plan-preview" aria-labelledby="plan-title">
            <div className="plan-preview-heading">
              <div><p className="eyebrow">{generatedPlan.engine}</p><h3 id="plan-title">{generatedPlan.title}</h3></div>
              <div className="plan-preview-actions">
                <span className="plan-style">{generatedPlan.dietStyle}</span>
                {[...(generatedPlan.excludedAllergens ?? []).map((item) => item.replace('_', ' ')), ...(generatedPlan.excludedIngredients ?? [])].length > 0 && <span className="plan-style">Avoiding: {[...(generatedPlan.excludedAllergens ?? []).map((item) => item.replace('_', ' ')), ...(generatedPlan.excludedIngredients ?? [])].join(', ')}</span>}
                {localPlanFileReady && <button type="button" className="download-button" onClick={handleDownloadPlan}>Download JSON</button>}
              </div>
            </div>
            <p className="plan-disclaimer">Meal ideas are for general information, not medical advice. Review ingredients and food labels yourself. A JSON copy is also kept in this browser.</p>
            <div className="plan-days">
              {generatedPlan.days.map((day) => <article className="plan-day" key={day.day}>
                <h4>Day {day.day}</h4>
                <dl>
                  <div><dt>Breakfast</dt><dd>{day.breakfast}<small className="meal-ingredients">Ingredients: {day.breakfastIngredients?.length ? day.breakfastIngredients.join(', ') : 'details unavailable for this older saved plan'}</small></dd></div>
                  <div><dt>Lunch</dt><dd>{day.lunch}<small className="meal-ingredients">Ingredients: {day.lunchIngredients?.length ? day.lunchIngredients.join(', ') : 'details unavailable for this older saved plan'}</small></dd></div>
                  <div><dt>Dinner</dt><dd>{day.dinner}<small className="meal-ingredients">Ingredients: {day.dinnerIngredients?.length ? day.dinnerIngredients.join(', ') : 'details unavailable for this older saved plan'}</small></dd></div>
                </dl>
              </article>)}
            </div>
            <ul className="plan-notes">{generatedPlan.notes.filter((note) => !note.startsWith('No exact ingredient match was found')).map((note) => <li key={note}>{note}</li>)}</ul>
          </section> : <p className="submission-message">No saved plans yet. Return to your profile and generate a meal plan.</p>}
          </>}
        </section>
      </main>
      <footer className="footer"><span>nourish<span className="brand-dot">.</span></span><span>Small steps, made personal.</span></footer>
    </div>
  )
}

function App() {
  const [user, setUser] = useState(undefined)

  useEffect(() => onAuthStateChanged(auth, setUser), [])

  if (user === undefined) {
    return <main className="auth-loading" aria-live="polite">Loading your account…</main>
  }

  if (!user) {
    return <AuthPanel />
  }

  return <PlannerForm user={user} onSignOut={() => signOut(auth)} />
}

createRoot(document.getElementById('root')).render(<App />)
