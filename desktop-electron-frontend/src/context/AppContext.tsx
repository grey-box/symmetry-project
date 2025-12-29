import { createContext, Dispatch, ReactNode, SetStateAction, useContext, useState } from 'react'
import { TranslationTool } from '@/models/enums/TranslationTool'

type AppContextType = {
  translationTool: TranslationTool;
  APIKey: string;
  setTranslationTool: Dispatch<SetStateAction<TranslationTool>>;
  setAPIKey: Dispatch<SetStateAction<string>>;
};

const APP_CONTEXT_DEFAULT_VALUES: AppContextType = {
  translationTool: TranslationTool.GOOGLE,
  APIKey: '',
  setAPIKey: () => {
  },
  setTranslationTool: () => {
  },
}
export const AppContext = createContext<AppContextType>(
  APP_CONTEXT_DEFAULT_VALUES,
)

type AppContextProviderProps = {
  children: ReactNode;
};

export const AppContextProvider = (props: AppContextProviderProps) => {
  const { children } = props
  const [translationTool, setTranslationTool] = useState()
  const [APIKey, setAPIKey] = useState()

  return (
    <AppContext.Provider
      value={{
        APIKey: '',
        translationTool: TranslationTool.GOOGLE,
        setTranslationTool,
        setAPIKey,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export const useAppContext = () => {
  return useContext(AppContext)
}
