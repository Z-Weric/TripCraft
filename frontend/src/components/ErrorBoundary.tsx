import { Component, type ReactNode } from "react";
import { Alert, Button } from "antd";

interface Props {
  children: ReactNode;
}
interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="max-w-2xl mx-auto p-6">
          <Alert
            type="error"
            message="页面出错了"
            description={this.state.error?.message || "发生了未知错误"}
            showIcon
            action={
              <Button size="small" onClick={this.handleReset}>
                重试
              </Button>
            }
          />
        </div>
      );
    }
    return this.props.children;
  }
}