import fs from 'node:fs'

import type { AnswerObject, IntentObject } from '@bridge/types'
import { VERSION } from '@bridge/version'
import type { Versions } from '@sdk/types'
import type { Answer } from '@sdk/answer'

class Leon {
  private static instance: Leon
  private static DEFAULT_INTENT_OBJECT = {} as IntentObject
  private _intentObject: IntentObject

  private constructor() {
    this._intentObject = Leon.DEFAULT_INTENT_OBJECT
  }

  public static getInstance(): Leon {
    if (Leon.instance == null) {
      Leon.instance = new Leon()
    }
    return Leon.instance
  }

  public get intentObject(): Readonly<IntentObject> {
    return Object.freeze(this._intentObject)
  }

  public get versions(): Versions {
    return {
      // TODO: get leon version dynamically from `package.json`
      core: '1.0.0-beta.9+dev',
      'nodejs-bridge': VERSION
    }
  }

  /**
   * Send an answer to the core
   * @param answer
   */
  public async answer(answer: Answer): Promise<void> {
    try {
      const answerObject: AnswerObject = {
        ...(await this.getIntentObject()),
        output: await answer.createAnswerOutput()
      }
      process.stdout.write(JSON.stringify(answerObject))
    } catch (error) {
      console.error('Error creating answer:', error)
    }
  }

  /**
   * Get the intent object from the temporary intent file
   * @example await getIntentObject() // { ... }
   */
  public async getIntentObject(): Promise<IntentObject> {
    const {
      argv: [, , INTENT_OBJ_FILE_PATH]
    } = process
    const intentObject = JSON.parse(
      await fs.promises.readFile(INTENT_OBJ_FILE_PATH as string, 'utf8')
    )
    this._intentObject = intentObject
    return this.intentObject
  }
}

export const leon = Leon.getInstance()
