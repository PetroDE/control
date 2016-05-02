node {
    step 'Checkout'
    checkout scm
    step 'Test'
    sh "./tests.sh"
    step([$class: 'JUnitResultArchiver', testResults: 'results.xml'])
}
