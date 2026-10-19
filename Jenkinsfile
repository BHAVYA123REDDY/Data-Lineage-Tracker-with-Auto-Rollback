pipeline {
  agent any
  environment {
    IMAGE_NAME = "data-lineage-tracker"
  }
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }
    stage('Build Docker image') {
      steps {
        bat """
          docker build -t %IMAGE_NAME%:%BUILD_NUMBER% -t %IMAGE_NAME%:latest .
        """
      }
    }
    stage('Run tests') {
      steps {
        bat """
          docker run --rm %IMAGE_NAME%:%BUILD_NUMBER% python test_database.py ^
            && docker run --rm %IMAGE_NAME%:%BUILD_NUMBER% python test_pipeline.py ^
            && docker run --rm %IMAGE_NAME%:%BUILD_NUMBER% python test_rollback.py ^
            && docker run --rm %IMAGE_NAME%:%BUILD_NUMBER% python test_app.py ^
            && docker run --rm %IMAGE_NAME%:%BUILD_NUMBER% python test_config.py
        """
      }
    }
    stage('Application health smoke test') {
      steps {
        bat """
          docker run -d --name lineage-smoke-%BUILD_NUMBER% -p 5001:5000 %IMAGE_NAME%:%BUILD_NUMBER%
          timeout /t 10 /nobreak
          python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:5001/health', timeout=5).status == 200 else 1)"
          set EXITCODE=%ERRORLEVEL%
          docker stop lineage-smoke-%BUILD_NUMBER% 2>nul || exit 0
          docker rm lineage-smoke-%BUILD_NUMBER% 2>nul || exit 0
          exit /b %EXITCODE%
        """
      }
    }
  }
  post {
    always {
      // Defensive cleanup: remove smoke container if it still exists (only for this build)
      bat """
        docker rm -f lineage-smoke-%BUILD_NUMBER% 2>nul || exit 0
      """
    }
  }
}
