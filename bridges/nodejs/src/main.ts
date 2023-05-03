import path from 'node:path'

import { leon } from '@sdk/leon'
;(async (): Promise<void> => {
  const { domain, skill, action } = await leon.getIntentObject()

  try {
    const { [action]: actionFunction } = await import(
      path.join(
        process.cwd(),
        'skills',
        domain,
        skill,
        'src',
        'actions',
        `${action}.ts`
      )
    )

    await actionFunction()
  } catch (e) {
    console.error('Error while running action:', e)
  }
})()
