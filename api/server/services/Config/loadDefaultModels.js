const { EModelEndpoint } = require('librechat-data-provider');
const {
  getOpenAIModels,
  getGoogleModels,
  getBedrockModels,
  getAnthropicModels,
} = require('~/server/services/ModelService');
const { logger } = require('~/config');

/**
 * Loads the default models for the application.
 * @async
 * @function
 * @param {Express.Request} req - The Express request object.
 */
async function loadDefaultModels(req) {
  try {
    const {
      openAI,
      azureOpenAI,
      google,
      anthropic,
      azureAssistants,
      azureOpenAIFQ,
      custom,
    } = {
      openAI: process.env.OPENAI_MODELS || '',
      azureOpenAI: process.env.AZURE_OPENAI_MODELS || '',
      google: process.env.GOOGLE_MODELS || '',
      anthropic: process.env.ANTHROPIC_MODELS || '',
      azureAssistants: process.env.AZURE_ASSISTANTS_MODELS || '',
      azureOpenAIFQ: process.env.AZURE_OPENAI_MODELS_FQ || '',
      custom: process.env.CUSTOM_MODELS || '',
    };

    const [
      openAIModels,
      anthropicModels,
      azureOpenAImodels,
      assistants,
      azureAssistantsModels,
      googleModels,
      bedrockModels,
    ] = await Promise.all([
      getOpenAIModels({ user: req.user.id }).catch((error) => {
        logger.error('Error fetching OpenAI models:', error);
        return [];
      }),
      getAnthropicModels({ user: req.user.id }).catch((error) => {
        logger.error('Error fetching Anthropic models:', error);
        return [];
      }),
      getOpenAIModels({ user: req.user.id, azure: true }).catch((error) => {
        logger.error('Error fetching Azure OpenAI models:', error);
        return [];
      }),
      getOpenAIModels({ user: req.user.id, azure: false, plugins: true }).catch(
        (error) => {
          logger.error('Error fetching Plugin models:', error);
          return [];
        },
      ),
      getOpenAIModels({ assistants: true }).catch((error) => {
        logger.error('Error fetching OpenAI Assistants API models:', error);
        return [];
      }),
      getOpenAIModels({ azureAssistants: true }).catch((error) => {
        logger.error('Error fetching Azure OpenAI Assistants API models:', error);
        return [];
      }),
      Promise.resolve(getGoogleModels()).catch((error) => {
        logger.error('Error getting Google models:', error);
        return [];
      }),
      Promise.resolve(getBedrockModels()).catch((error) => {
        logger.error('Error getting Bedrock models:', error);
        return [];
      }),
    ]);

    return {
      [EModelEndpoint.openAI]: openAI,
      [EModelEndpoint.agents]: openAI,
      [EModelEndpoint.google]: google,
      [EModelEndpoint.anthropic]: anthropic,
      [EModelEndpoint.azureOpenAI]: azureOpenAI,
      [EModelEndpoint.assistants]: assistants,
      [EModelEndpoint.azureAssistants]: azureAssistants,
      [EModelEndpoint.bedrock]: bedrock,
    };
  } catch (error) {
    logger.error('Error fetching default models:', error);
    throw new Error(`Failed to load default models: ${error.message}`);
  }
}

module.exports = loadDefaultModels;
