pipeline {
  agent any
  environment {
    IMAGE_NAME = "data-lineage-tracker"
    DOCKER = "C:\\Users\\AASHITHA\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin\\docker.exe"
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
          "%DOCKER%" build -t %IMAGE_NAME%:%BUILD_NUMBER% -t %IMAGE_NAME%:latest .
        """
      }
    }
     stage('Run tests') {
      steps {
        bat """
          "%DOCKER%" run --rm --entrypoint python %IMAGE_NAME%:%BUILD_NUMBER% test_database.py ^
          && "%DOCKER%" run --rm --entrypoint python %IMAGE_NAME%:%BUILD_NUMBER% test_pipeline.py ^
          && "%DOCKER%" run --rm --entrypoint python %IMAGE_NAME%:%BUILD_NUMBER% test_rollback.py ^
          && "%DOCKER%" run --rm --entrypoint python %IMAGE_NAME%:%BUILD_NUMBER% test_app.py ^
          && "%DOCKER%" run --rm --entrypoint python %IMAGE_NAME%:%BUILD_NUMBER% test_config.py
        """
      }
    }
    stage('Application health smoke test') {
      steps {
        bat """
          "%DOCKER%" run -d --name lineage-smoke-%BUILD_NUMBER% -p 5001:5000 %IMAGE_NAME%:%BUILD_NUMBER%
          ping 127.0.0.1 -n 11 > nul
          "%DOCKER%" exec lineage-smoke-%BUILD_NUMBER% python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:5000/health', timeout=5).status == 200 else 1)"
          "%DOCKER%" exec lineage-smoke-%BUILD_NUMBER% python -c "import json,urllib.request; req=urllib.request.Request('http://localhost:5000/api/simulate', data=json.dumps({'source_name':'customers_csv','force_failure':True}).encode(), headers={'Content-Type':'application/json'}, method='POST'); r=json.load(urllib.request.urlopen(req, timeout=10)); print(r); assert r.get('rolled_back') is True, 'Automatic rollback did not occur'"
          set EXITCODE=%ERRORLEVEL%
          "%DOCKER%" stop lineage-smoke-%BUILD_NUMBER% 2>nul || exit 0
          "%DOCKER%" rm lineage-smoke-%BUILD_NUMBER% 2>nul || exit 0
          exit /b %EXITCODE%
        """
      }
    }
  }
  post {
    always {
      // Defensive cleanup: remove smoke container if it still exists (only for this build)
      bat """
       "%DOCKER%" rm -f lineage-smoke-%BUILD_NUMBER% 2>nul || exit 0
      """
    }
  }
}
