declare module 'react-quill' {
  import { Component } from 'react';

  export interface ReactQuillProps {
    value?: string;
    defaultValue?: string;
    onChange?: (value: string) => void;
    theme?: string;
    id?: string;
    className?: string;
    placeholder?: string;
    readOnly?: boolean;
    modules?: any;
    formats?: any;
  }

  export default class ReactQuill extends Component<ReactQuillProps> {}
}
