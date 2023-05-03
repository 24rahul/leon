import { AnswerObject, AnswerTypes } from '@bridge/types'

/**
 * Holds methods to communicate data from the skill to the core
 */

interface AnswerOptions {
  type: AnswerTypes
  text: string
}

export abstract class Answer implements AnswerOptions {
  public abstract type: AnswerTypes
  public abstract text: string

  /**
   * Create an answer object to send an answer to the core
   * @param type The type of the answer
   * @param text The text to send
   */
  public async createAnswerOutput(): Promise<AnswerObject['output']> {
    return {
      type: this.type,
      codes: '', // TODO
      speech: this.text,
      core: {}, // TODO
      options: {} // TODO
    }
  }
}

export class IntermediateAnswer extends Answer {
  public override type = AnswerTypes.Intermediate
  public override text: string

  /**
   * Create an answer object with the intermediate type
   * to send an intermediate answer to the core.
   * Used to send an answer before the final answer
   * @param text The text to send
   * @example new IntermediateAnswer('intermediate answer')
   */
  public constructor(text: string) {
    super()
    this.text = text
  }
}

export class FinalAnswer extends Answer {
  public override type = AnswerTypes.Final
  public override text: string

  /**
   * Create an answer object with the final type
   * to send a final answer to the core.
   * Used to send an answer before the end of the skill action
   * @param text The text to send
   * @example new FinalAnswer('final answer')
   */
  public constructor(text: string) {
    super()
    this.text = text
  }
}
