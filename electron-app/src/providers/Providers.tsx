import { FC, PropsWithChildren } from 'react';
import { LanguageProvider } from './LanguageProvider';

export const Providers: FC<PropsWithChildren> = ({ children }) => {
  return <LanguageProvider>{children}</LanguageProvider>;
};

export default Providers;
