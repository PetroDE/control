node {
    Step 'Checkout'
    checkout scm
    Step 'Test'
    sh "./tests.sh"
    step([$class: 'JUnitResultArchiver', testResults: 'results.xml'])
}
