const DATABASE_NAME = 'nourish-object-storage-simulator'
const STORE_NAME = 'plan-files'

function openStorageDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, 1)
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE_NAME, { keyPath: 'key' })
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function savePlanFile(userId, plan) {
  const database = await openStorageDatabase()
  const key = `users/${userId}/plans/${plan.planId}.json`

  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, 'readwrite')
    transaction.objectStore(STORE_NAME).put({
      key,
      ownerId: userId,
      fileName: `meal-plan-${plan.planId}.json`,
      contentType: 'application/json',
      savedAt: new Date().toISOString(),
      content: JSON.stringify(plan, null, 2),
    })
    transaction.oncomplete = () => {
      database.close()
      resolve(key)
    }
    transaction.onerror = () => {
      database.close()
      reject(transaction.error)
    }
    transaction.onabort = () => {
      database.close()
      reject(transaction.error)
    }
  })
}

export async function downloadPlanFile(userId, planId) {
  const database = await openStorageDatabase()
  const key = `users/${userId}/plans/${planId}.json`

  const record = await new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, 'readonly')
    const request = transaction.objectStore(STORE_NAME).get(key)
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  }).finally(() => database.close())

  if (!record || record.ownerId !== userId) {
    throw new Error('The local plan file was not found for this account.')
  }

  const file = new Blob([record.content], { type: record.contentType })
  const url = URL.createObjectURL(file)
  const link = document.createElement('a')
  link.href = url
  link.download = record.fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export async function hasPlanFile(userId, planId) {
  const database = await openStorageDatabase()
  const key = `users/${userId}/plans/${planId}.json`

  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, 'readonly')
    const request = transaction.objectStore(STORE_NAME).get(key)
    request.onsuccess = () => resolve(Boolean(request.result && request.result.ownerId === userId))
    request.onerror = () => reject(request.error)
    transaction.oncomplete = () => database.close()
    transaction.onerror = () => {
      database.close()
      reject(transaction.error)
    }
  })
}
