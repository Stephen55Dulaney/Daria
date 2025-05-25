"""OpenAI adapter for LangChain compatibility"""

import os
import logging
from typing import Any, Dict, List, Optional, Union, cast
import asyncio

# Try to import OpenAI or use the mock provider
try:
    from openai import OpenAI, AsyncOpenAI
    USING_OPENAI = True
except ImportError:
    from mock_openai_provider import provider
    USING_OPENAI = False

# LangChain imports
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
from langchain.schema import LLMResult, Generation, BaseMessage
from langchain.schema.output import ChatGeneration, ChatResult

logger = logging.getLogger(__name__)

class OpenAILangChainAdapter(LLM):
    """Adapter to use OpenAI with LangChain"""
    
    model_name: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 500
    
    @property
    def _llm_type(self) -> str:
        return "openai-adapter"
    
    def _call(
        self, 
        prompt: str, 
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> str:
        """Call the OpenAI API or mock provider"""
        try:
            if USING_OPENAI:
                client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                response = client.completions.create(
                    model=self.model_name,
                    prompt=prompt,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stop=stop
                )
                return response.choices[0].text.strip()
            else:
                response = provider.complete(prompt)
                return response["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Error calling OpenAI: {str(e)}")
            return "I'm sorry, I encountered an error processing that request."
    
    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs
    ) -> str:
        """Async version of call"""
        try:
            if USING_OPENAI:
                client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                response = await client.completions.create(
                    model=self.model_name,
                    prompt=prompt,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stop=stop
                )
                return response.choices[0].text.strip()
            else:
                # For mock provider, simulate async
                await asyncio.sleep(0.1)
                response = provider.complete(prompt)
                return response["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Error in async OpenAI call: {str(e)}")
            return "I'm sorry, I encountered an error processing that request."
    
    def generate(
        self, 
        prompts: List[str], 
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> LLMResult:
        """Generate text from multiple prompts"""
        generations = []
        for prompt in prompts:
            text = self._call(prompt, stop, run_manager, **kwargs)
            generations.append([Generation(text=text)])
        return LLMResult(generations=generations)
    
    async def agenerate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs
    ) -> LLMResult:
        """Async version of generate"""
        generations = []
        for prompt in prompts:
            text = await self._acall(prompt, stop, run_manager, **kwargs)
            generations.append([Generation(text=text)])
        return LLMResult(generations=generations)
    
    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> LLMResult:
        """Internal generate method that returns LLMResult"""
        return self.generate(prompts, stop, run_manager, **kwargs)
    
    async def _agenerate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs
    ) -> LLMResult:
        """Async version of _generate"""
        return await self.agenerate(prompts, stop, run_manager, **kwargs)
    
    def generate_prompt(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> LLMResult:
        """Generate from prompts"""
        return self.generate(prompts, stop, run_manager, **kwargs)
    
    async def agenerate_prompt(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs
    ) -> LLMResult:
        """Async version of generate_prompt"""
        return await self.agenerate(prompts, stop, run_manager, **kwargs)
    
    def predict(
        self,
        text: str,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Predict text"""
        return self._call(text, stop, **kwargs)
    
    async def apredict(
        self,
        text: str,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Async version of predict"""
        return await self._acall(text, stop, **kwargs)
    
    def predict_messages(
        self,
        messages: List[Dict[str, str]],
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Predict from messages"""
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        return self._call(prompt, stop, **kwargs)
    
    async def apredict_messages(
        self,
        messages: List[Dict[str, str]],
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Async version of predict_messages"""
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        return await self._acall(prompt, stop, **kwargs)
    
    def invoke(
        self,
        input: Union[str, List[BaseMessage]],
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Invoke the model"""
        if isinstance(input, str):
            return self._call(input, stop, **kwargs)
        else:
            return self.predict_messages([{"role": m.type, "content": m.content} for m in input], stop, **kwargs)
    
    async def ainvoke(
        self,
        input: Union[str, List[BaseMessage]],
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Async version of invoke"""
        if isinstance(input, str):
            return await self._acall(input, stop, **kwargs)
        else:
            return await self.apredict_messages([{"role": m.type, "content": m.content} for m in input], stop, **kwargs)
